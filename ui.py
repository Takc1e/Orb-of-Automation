import tkinter as tk
from tkinter import scrolledtext, ttk
import keyboard
import pyautogui
import pyperclip

from i18n import LANGUAGES, get_text
from parsers import normalize_text, parse_item_mod_lines, read_int_or_none
from regex_utils import compile_regex
from roller import Roller


CURRENCY_BOX_PRESET = {
    # Normalized centers inside the whole visible currency stash tab.
    # Capture the outer top-left and bottom-right corners of the stash panel.
    "transmute": (0.060, 0.216),
    "alteration": (0.150, 0.216),
    "annul": (0.240, 0.216),
    "augment": (0.329, 0.306),
    "exalt": (0.456, 0.216),
    "regal": (0.670, 0.216),
    "scour": (0.670, 0.417),
    "item": (0.497, 0.523),
}


class AutoAlterationOrbApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Orb of Automation")
        self.root.geometry("1280x1100")
        self.root.minsize(1120, 980)

        self.roller = Roller(self.log)
        self.captured_positions = {}
        self.currency_box = {}
        self.language = "en"
        self.i18n_widgets = []
        self.i18n_label_frames = []
        self.i18n_tabs = {}
        self.map_field_labels = {}
        self.position_name_labels = {}
        self.cluster_target_labels = []

        self.build_ui()
        self.register_hotkeys()

    def run(self):
        self.root.mainloop()

    def log(self, message):
        self.output_box.insert(tk.END, message + "\n")
        self.output_box.see(tk.END)

    def tr(self, key: str) -> str:
        return get_text(self.language, key)

    def make_label(self, parent, key: str, **kwargs):
        label = tk.Label(parent, text=self.tr(key), **kwargs)
        self.i18n_widgets.append((label, key))
        return label

    def make_button(self, parent, key: str, **kwargs):
        button = tk.Button(parent, text=self.tr(key), **kwargs)
        self.i18n_widgets.append((button, key))
        return button

    def make_radiobutton(self, parent, key: str, **kwargs):
        button = tk.Radiobutton(parent, text=self.tr(key), **kwargs)
        self.i18n_widgets.append((button, key))
        return button

    def make_checkbutton(self, parent, key: str, **kwargs):
        button = tk.Checkbutton(parent, text=self.tr(key), **kwargs)
        self.i18n_widgets.append((button, key))
        return button

    def make_label_frame(self, parent, key: str, **kwargs):
        frame = tk.LabelFrame(parent, text=self.tr(key), **kwargs)
        self.i18n_label_frames.append((frame, key))
        return frame

    def on_language_changed(self, event=None):
        selected_label = self.language_var.get()
        reverse_map = {label: code for code, label in LANGUAGES.items()}
        self.language = reverse_map.get(selected_label, "en")
        self.apply_language()

    def apply_language(self):
        for widget, key in self.i18n_widgets:
            widget.config(text=self.tr(key))

        for frame, key in self.i18n_label_frames:
            frame.config(text=self.tr(key))

        for tab, key in self.i18n_tabs.items():
            self.notebook.tab(tab, text=self.tr(key))

        for key, label in self.map_field_labels.items():
            label.config(text=self.tr(key))

        for key, label in self.position_name_labels.items():
            label.config(text=f"{self.tr(key)}:")

        for index, label in enumerate(self.cluster_target_labels):
            label.config(text=f"{self.tr('target')} {index + 1}:")

        self.on_tab_changed()

    def capture_position(self, key: str, label_widget: tk.Label):
        label_widget.config(text="capturing...")
        self.log(f"Move your mouse to {key}. Capturing in 3 seconds.")
        self.root.after(3000, lambda: self.finish_capture_position(key, label_widget))

    def finish_capture_position(self, key: str, label_widget: tk.Label):
        position = pyautogui.position()
        self.captured_positions[key] = (position.x, position.y)
        label_widget.config(text=f"{position.x}, {position.y}")
        self.log(f"Captured {key}: {position.x}, {position.y}")
        self.show_capture_overlay({key: self.captured_positions[key]}, duration_ms=1500)

    def capture_currency_box_corner(self, corner: str):
        label = self.tr("currency_box_top_left") if corner == "top_left" else self.tr("currency_box_bottom_right")
        self.log(f"Move your mouse to {label}. Capturing in 3 seconds.")
        self.root.after(3000, lambda: self.finish_capture_currency_box_corner(corner))

    def finish_capture_currency_box_corner(self, corner: str):
        position = pyautogui.position()
        point = (position.x, position.y)
        self.currency_box[corner] = point
        self.captured_positions[f"currency_box_{corner}"] = point
        self.log(f"Captured currency box {corner}: {point[0]}, {point[1]}")

        if len(self.currency_box) == 2:
            self.auto_fill_from_currency_box()
        else:
            self.show_capture_overlay({f"currency_box_{corner}": point}, duration_ms=1500)

    def auto_fill_from_currency_box(self):
        top_left = self.currency_box.get("top_left")
        bottom_right = self.currency_box.get("bottom_right")

        if not top_left or not bottom_right:
            self.log("Capture currency box top-left and bottom-right first.")
            return

        left = min(top_left[0], bottom_right[0])
        right = max(top_left[0], bottom_right[0])
        top = min(top_left[1], bottom_right[1])
        bottom = max(top_left[1], bottom_right[1])
        width = right - left
        height = bottom - top

        if width < 200 or height < 200:
            self.log("Currency box is too small. Capture the whole visible currency stash tab.")
            return

        filled_positions = {
            key: (
                int(round(left + width * normalized_x)),
                int(round(top + height * normalized_y)),
            )
            for key, (normalized_x, normalized_y) in CURRENCY_BOX_PRESET.items()
        }

        for key, position in filled_positions.items():
            self.captured_positions[key] = position

            if key in self.cluster_position_labels:
                self.cluster_position_labels[key].config(
                    text=f"{position[0]}, {position[1]}"
                )

        self.log("Auto-filled cluster positions from currency stash box.")
        overlay_positions = {
            "box top-left": (left, top),
            "box bottom-right": (right, bottom),
            **filled_positions,
        }
        self.show_capture_overlay(overlay_positions)

    def clear_cluster_selection(self):
        self.currency_box.clear()

        keys_to_clear = set(CURRENCY_BOX_PRESET)
        keys_to_clear.update({"currency_box_top_left", "currency_box_bottom_right"})

        for key in keys_to_clear:
            self.captured_positions.pop(key, None)

            if key in self.cluster_position_labels:
                self.cluster_position_labels[key].config(text=self.tr("not_captured"))

        self.log("Cleared cluster capture selection.")

    def show_capture_overlay(self, positions=None, duration_ms=6000):
        positions = positions or {
            key: value
            for key, value in self.captured_positions.items()
            if value
        }

        if not positions:
            self.log("No captured positions to show.")
            return

        screen_width, screen_height = pyautogui.size()
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.geometry(f"{screen_width}x{screen_height}+0+0")

        transparent_color = "#ff00ff"
        canvas = tk.Canvas(
            overlay,
            width=screen_width,
            height=screen_height,
            bg=transparent_color,
            highlightthickness=0,
        )
        canvas.pack(fill="both", expand=True)

        try:
            overlay.attributes("-transparentcolor", transparent_color)
        except tk.TclError:
            overlay.attributes("-alpha", 0.75)

        if (
            "box top-left" in positions
            and "box bottom-right" in positions
        ):
            left, top = positions["box top-left"]
            right, bottom = positions["box bottom-right"]
            canvas.create_rectangle(
                left,
                top,
                right,
                bottom,
                outline="#00ff66",
                width=2,
            )

        for label, (x, y) in positions.items():
            canvas.create_oval(
                x - 12,
                y - 12,
                x + 12,
                y + 12,
                outline="#00ff66",
                width=3,
            )
            canvas.create_line(x - 20, y, x + 20, y, fill="#00ff66", width=2)
            canvas.create_line(x, y - 20, x, y + 20, fill="#00ff66", width=2)
            canvas.create_text(
                x + 10,
                y - 24,
                text=label,
                fill="#00ff66",
                anchor="sw",
                font=("Arial", 14, "bold"),
            )

        overlay.after(duration_ms, overlay.destroy)

    def preview_copied_item_text(self):
        item_position = self.captured_positions.get("item")

        if item_position:
            pyautogui.moveTo(item_position[0], item_position[1])

        pyautogui.keyUp("shift")
        pyautogui.hotkey("ctrl", "alt", "c")
        self.root.after(150, self.finish_preview_copied_item_text)

    def finish_preview_copied_item_text(self):
        text = normalize_text(pyperclip.paste())
        lines = [line for line in text.splitlines() if line.strip()]

        if not lines:
            self.log("Copied item text is empty. Hover the item or capture Jewel / Item first.")
            return

        self.log("Copied item text preview:")
        for line in lines[:18]:
            self.log(f"  {line}")

        if len(lines) > 18:
            self.log(f"  ... {len(lines) - 18} more lines")

        mod_lines = parse_item_mod_lines(text)

        self.log(f"Parsed explicit mods ({len(mod_lines)}):")
        for line in mod_lines:
            self.log(f"  {line}")

        target_matches = []

        for index, entry in enumerate(getattr(self, "cluster_target_entries", [])):
            target_text = entry.get().strip()

            if not target_text:
                continue

            try:
                target_regex = compile_regex(target_text, f"target {index + 1}")
            except ValueError as e:
                self.log(str(e))
                continue

            if target_regex and target_regex.search(text):
                target_matches.append(index + 1)

        self.log(f"Preview target matches: {target_matches}")

    def build_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill="x", anchor="n")

        language_frame = tk.Frame(main_frame)
        language_frame.pack(anchor="e", fill="x", pady=(0, 6))

        self.language_selector = ttk.Combobox(
            language_frame,
            values=list(LANGUAGES.values()),
            state="readonly",
            width=18,
        )
        self.language_selector.pack(side="right", padx=(6, 0))
        self.make_label(language_frame, "language").pack(side="right")
        self.language_var = tk.StringVar(value=LANGUAGES[self.language])
        self.language_selector.config(textvariable=self.language_var)
        self.language_selector.bind("<<ComboboxSelected>>", self.on_language_changed)

        self.notebook = ttk.Notebook(top_frame)
        self.notebook.pack(side="left", anchor="n", fill="both", expand=False)
        self.notebook.config(width=1240, height=760)

        self.item_tab = tk.Frame(self.notebook)
        self.map_tab = tk.Frame(self.notebook)
        self.cluster_tab = tk.Frame(self.notebook)

        self.notebook.add(self.item_tab, text=self.tr("item_tab"))
        self.notebook.add(self.map_tab, text=self.tr("map_tab"))
        self.notebook.add(self.cluster_tab, text=self.tr("cluster_tab"))
        self.i18n_tabs = {
            self.item_tab: "item_tab",
            self.map_tab: "map_tab",
            self.cluster_tab: "cluster_tab",
        }

        self.build_item_tab()
        self.build_map_tab()
        self.build_cluster_tab()

        self.build_control_panel(main_frame)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.on_tab_changed()

        self.output_box = scrolledtext.ScrolledText(
            main_frame,
            width=130,
            height=7,
        )
        self.output_box.pack(anchor="w", fill="x", padx=0, pady=(8, 0))

        self.log("Ready. Press F6 to start and F7 to stop")

    def build_item_tab(self):
        self.make_label(self.item_tab, "target_mod_keyword").pack(anchor="w", padx=10, pady=(10, 0))

        self.item_regex_entry = tk.Entry(self.item_tab, width=60)
        self.item_regex_entry.pack(anchor="w", padx=10, pady=5)

        tk.Label(
            self.item_tab,
            text="e.g. \nof the prodigy | meteor\nincreased effect of tailwind | onslaught\n强大的|奇才之\n提速尾流|中毒\nAll Languages supported",
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=10, pady=(10, 0))

    def build_map_tab(self):
        self.make_label(self.map_tab, "map_avoid_regex").pack(anchor="w", padx=10, pady=(10, 0))

        self.map_avoid_regex_entry = tk.Entry(self.map_tab, width=60)
        self.map_avoid_regex_entry.pack(anchor="w", padx=10, pady=5)

        tk.Label(
            self.map_tab,
            text='e.g. "!ur$|h vu|ot i","Block|reflect|regen", "焚界者符文|反射|无法回复"',
            anchor="w",
        ).pack(anchor="w", padx=10)

        frame = tk.Frame(self.map_tab)
        frame.pack(anchor="w", padx=10, pady=10)

        self.map_entries = {}

        fields = [
            ("quantity", "Quantity >="),
            ("pack_size", "Pack Size >="),
            ("rarity", "Item Rarity >="),
            ("more_maps", "More Maps >="),
            ("currency", "Currency >="),
            ("scarabs", "Scarabs >="),
            ("divination", "Divination >="),
        ]

        for i, (key, label) in enumerate(fields):
            field_label = tk.Label(frame, text=self.tr(key), width=18, anchor="w")
            field_label.grid(
                row=i,
                column=0,
                sticky="w",
                pady=2,
            )
            self.map_field_labels[key] = field_label

            entry = tk.Entry(frame, width=12)
            entry.grid(row=i, column=1, sticky="w", pady=2)

            self.map_entries[key] = entry

        self.make_label(self.map_tab, "empty_fields_ignored").pack(anchor="w", padx=10, pady=(5, 0))

    def build_cluster_tab(self):
        left_frame = tk.Frame(self.cluster_tab)
        left_frame.grid(row=0, column=0, sticky="nw", padx=10, pady=10)

        right_frame = tk.Frame(self.cluster_tab)
        right_frame.grid(row=0, column=1, sticky="nw", padx=20, pady=10)
        self.cluster_tab.grid_columnconfigure(0, weight=1)
        self.cluster_tab.grid_columnconfigure(1, weight=1)

        self.make_label(left_frame, "target_mods").pack(anchor="w")

        self.cluster_target_entries = []

        for index in range(4):
            row = tk.Frame(left_frame)
            row.pack(anchor="w", pady=2)

            target_label = tk.Label(row, text=f"{self.tr('target')} {index + 1}:", width=10, anchor="w")
            target_label.pack(side="left")
            self.cluster_target_labels.append(target_label)

            entry = tk.Entry(row, width=52)
            entry.pack(side="left")
            self.cluster_target_entries.append(entry)

        self.make_label(
            left_frame,
            "cluster_target_warning",
            justify="left",
            anchor="w",
            wraplength=430,
        ).pack(anchor="w", pady=(4, 8))

        self.fractured_var = tk.BooleanVar(value=False)
        self.fractured_checkbox = self.make_checkbutton(
            left_frame,
            "fractured_checkbox",
            variable=self.fractured_var,
        )
        self.fractured_checkbox.pack(anchor="w", pady=(12, 2))

        fractured_row = tk.Frame(left_frame)
        fractured_row.pack(anchor="w", pady=2)

        self.make_label(fractured_row, "fractured", width=10, anchor="w").pack(side="left")
        self.fractured_entry = tk.Entry(fractured_row, width=52)
        self.fractured_entry.pack(side="left")

        self.make_label(
            left_frame,
            "fractured_hint",
            anchor="w",
        ).pack(anchor="w", pady=(4, 10))

        self.stop_at_three_var = tk.BooleanVar(value=False)
        self.make_checkbutton(
            left_frame,
            "stop_at_three_targets",
            variable=self.stop_at_three_var,
        ).pack(anchor="w", pady=(2, 10))

        position_frame = self.make_label_frame(right_frame, "screen_positions")
        position_frame.pack(anchor="w", fill="x", pady=(5, 0))

        self.cluster_position_labels = {}
        position_fields = [
            ("item", "Jewel / Item"),
            ("alteration", "Alteration"),
            ("augment", "Augment"),
            ("regal", "Regal"),
            ("exalt", "Exalt"),
            ("annul", "Annul"),
            ("scour", "Scour"),
            ("transmute", "Transmute"),
        ]

        for row_index, (key, label) in enumerate(position_fields):
            name_label = tk.Label(position_frame, text=f"{self.tr(key)}:", width=14, anchor="w")
            name_label.grid(
                row=row_index,
                column=0,
                sticky="w",
                padx=6,
                pady=2,
            )
            self.position_name_labels[key] = name_label

            value_label = tk.Label(position_frame, text=self.tr("not_captured"), width=16, anchor="w")
            value_label.grid(row=row_index, column=1, sticky="w", padx=6, pady=2)
            self.cluster_position_labels[key] = value_label

            self.make_button(
                position_frame,
                "capture",
                command=lambda name=key, widget=value_label: self.capture_position(name, widget),
            ).grid(row=row_index, column=2, sticky="w", padx=6, pady=2)

        box_row = len(position_fields)
        self.make_button(
            position_frame,
            "currency_box_top_left",
            command=lambda: self.capture_currency_box_corner("top_left"),
        ).grid(row=box_row, column=0, sticky="w", padx=6, pady=(8, 2))

        self.make_button(
            position_frame,
            "currency_box_bottom_right",
            command=lambda: self.capture_currency_box_corner("bottom_right"),
        ).grid(row=box_row, column=1, columnspan=2, sticky="w", padx=6, pady=(8, 2))

        self.make_button(
            position_frame,
            "clear_selection",
            command=self.clear_cluster_selection,
        ).grid(row=box_row + 1, column=0, columnspan=3, sticky="w", padx=6, pady=(2, 6))

        utility_frame = tk.Frame(right_frame)
        utility_frame.pack(anchor="w", fill="x", pady=(6, 4))

        self.make_button(
            utility_frame,
            "show_captures",
            command=self.show_capture_overlay,
        ).pack(side="left", padx=(0, 8))

        self.make_button(
            utility_frame,
            "preview_copied_item_text",
            command=self.preview_copied_item_text,
        ).pack(side="left")

        self.make_label(
            right_frame,
            "currency_box_hint",
            anchor="w",
            justify="left",
            wraplength=440,
        ).pack(anchor="w", pady=(2, 4))

        self.make_label(
            right_frame,
            "cluster_position_hint",
            anchor="w",
            justify="left",
            wraplength=440,
        ).pack(anchor="w", pady=(2, 0))

    def build_control_panel(self, parent):
        panel = self.make_label_frame(parent, "controls")
        panel.pack(anchor="w", fill="x", pady=(10, 0))

        self.make_label(panel, "max_attempt").grid(row=0, column=0, sticky="w", padx=(10, 4), pady=8)

        self.limit_entry = tk.Entry(panel, width=10)
        self.limit_entry.insert(0, "40")
        self.limit_entry.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=8)

        self.currency_mode_var = tk.StringVar(value="single")

        self.single_currency_radio = self.make_radiobutton(
            panel,
            "chaos_orb",
            variable=self.currency_mode_var,
            value="single",
        )
        self.single_currency_radio.grid(row=0, column=2, sticky="w", padx=(0, 12), pady=8)

        self.extra_currency_radio = self.make_radiobutton(
            panel,
            "chaos_exalt_once",
            variable=self.currency_mode_var,
            value="extra",
        )
        self.extra_currency_radio.grid(row=0, column=3, sticky="w", padx=(0, 20), pady=8)

        self.alch_scour_radio = self.make_radiobutton(
            panel,
            "alchemy_scouring",
            variable=self.currency_mode_var,
            value="alch_scour",
        )
        self.alch_scour_radio.grid(row=1, column=2, columnspan=2, sticky="w", padx=(0, 20), pady=(0, 8))

        self.shortcut_label = self.make_label(panel, "alternate_currency_input")
        self.shortcut_label.grid(row=0, column=4, sticky="e", padx=(0, 4), pady=8)

        self.shortcut_entry = tk.Entry(panel, width=10)
        self.shortcut_entry.insert(0, "alt")
        self.shortcut_entry.grid(row=0, column=5, sticky="w", padx=(0, 20), pady=8)

        self.make_label(panel, "speed").grid(row=0, column=6, sticky="w", padx=(0, 4), pady=8)

        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_slider = tk.Scale(
            panel,
            from_=0.5,
            to=2.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.speed_var,
            length=200,
        )
        self.speed_slider.grid(row=0, column=7, sticky="w", padx=(0, 10), pady=8)

        self.make_label(panel, "hotkeys").grid(
            row=2,
            column=0,
            columnspan=8,
            sticky="w",
            padx=(10, 10),
            pady=(0, 8),
        )

    def on_tab_changed(self, event=None):
        tab = self.notebook.index(self.notebook.select())

        self.shortcut_label.grid()
        self.shortcut_entry.grid()
        self.alch_scour_radio.grid_remove()

        if tab == 0:
            if self.currency_mode_var.get() == "alch_scour":
                self.currency_mode_var.set("single")

            self.single_currency_radio.config(text=self.tr("no_augment"))
            self.extra_currency_radio.config(text=self.tr("use_augment_orb"))
            self.shortcut_label.config(text=self.tr("alternate_currency_input"))
            self.shortcut_entry.delete(0, tk.END)
            self.shortcut_entry.insert(0, "alt")

        elif tab == 1:
            self.single_currency_radio.config(text=self.tr("chaos_orb"))
            self.extra_currency_radio.config(text=self.tr("chaos_exalt_once"))
            self.alch_scour_radio.config(text=self.tr("alchemy_scouring"))
            self.alch_scour_radio.grid()
            self.shortcut_label.config(text=self.tr("alternate_currency_input"))
            self.shortcut_entry.delete(0, tk.END)
            self.shortcut_entry.insert(0, "alt")

        else:
            if self.currency_mode_var.get() == "alch_scour":
                self.currency_mode_var.set("single")

            self.single_currency_radio.config(text=self.tr("alter_only"))
            self.extra_currency_radio.config(text=self.tr("use_augment_at_1"))
            self.shortcut_label.config(text=self.tr("augment_shortcut"))
            self.shortcut_entry.delete(0, tk.END)
            self.shortcut_entry.insert(0, "alt")

    def register_hotkeys(self):
        try:
            keyboard.add_hotkey("f6", self.request_start, suppress=False)
            keyboard.add_hotkey("f8", self.request_start, suppress=False)
            keyboard.add_hotkey("f7", self.request_stop, suppress=False)
            self.log("Hotkeys registered: F6/F8 start, F7 stop")
        except Exception as e:
            self.log(f"Hotkeys failed to register: {e}")
            self.log("Use the Start and Stop buttons instead, or run as Administrator.")

    def request_start(self):
        self.root.after(0, self.start_current_tab)

    def request_stop(self):
        self.root.after(0, self.roller.stop)

    def get_common_settings(self):
        try:
            max_attempts = int(self.limit_entry.get())
        except ValueError:
            max_attempts = 40

        return {
            "max_attempts": max_attempts,
            "speed": self.speed_var.get(),
            "use_extra_currency": self.currency_mode_var.get() == "extra",
            "currency_mode": self.currency_mode_var.get(),
            "shortcut_key": self.shortcut_entry.get().strip().lower() or "alt",
        }

    def start_current_tab(self):
        self.log("Start requested.")

        tab = self.notebook.index(self.notebook.select())
        settings = self.get_common_settings()

        if tab == 0:
            settings["item_regex"] = self.item_regex_entry.get()
            self.roller.start_item_thread(settings)

        elif tab == 1:
            settings["map_avoid_regex"] = self.map_avoid_regex_entry.get()
            settings["map_thresholds"] = {
                key: read_int_or_none(entry.get())
                for key, entry in self.map_entries.items()
            }
            self.roller.start_map_thread(settings)

        else:
            settings["cluster_targets"] = [
                entry.get()
                for entry in self.cluster_target_entries
            ]
            settings["is_fractured"] = self.fractured_var.get()
            settings["fractured_mod"] = self.fractured_entry.get()
            settings["stop_at_three_targets"] = self.stop_at_three_var.get()

            for key in [
                "alteration_key",
                "augment_key",
                "regal_key",
                "exalt_key",
                "annul_key",
                "scour_key",
                "transmute_key",
            ]:
                settings[key] = ""

            settings["item_position"] = self.captured_positions.get("item")
            settings["currency_positions"] = {
                key: self.captured_positions.get(key)
                for key in [
                "alteration",
                "augment",
                "regal",
                "exalt",
                    "annul",
                    "scour",
                    "transmute",
                ]
            }

            self.roller.start_cluster_thread(settings)
