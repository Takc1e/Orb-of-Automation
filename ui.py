import tkinter as tk
from tkinter import scrolledtext, ttk
import keyboard

from parsers import read_int_or_none
from roller import Roller


class AutoAlterationOrbApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AutoAlterationOrb")
        self.root.geometry("750x700")

        self.roller = Roller(self.log)

        self.build_ui()
        self.register_hotkeys()

    def run(self):
        self.root.mainloop()

    def log(self, message):
        self.output_box.insert(tk.END, message + "\n")
        self.output_box.see(tk.END)

    def build_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill="x", anchor="n")

        self.notebook = ttk.Notebook(top_frame)
        self.notebook.pack(side="left", anchor="n", fill="both", expand=False)
        self.notebook.config(width=780, height=430)

        self.item_tab = tk.Frame(self.notebook)
        self.map_tab = tk.Frame(self.notebook)

        self.notebook.add(self.item_tab, text="Item")
        self.notebook.add(self.map_tab, text="Map")

        self.build_item_tab()
        self.build_map_tab()

        self.build_control_panel(top_frame)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.on_tab_changed()

        self.output_box = scrolledtext.ScrolledText(
            main_frame,
            width=130,
            height=10,
        )
        self.output_box.pack(anchor="w", padx=0, pady=(15, 0))

        self.log("Ready. Press F6 to start and F7 to stop")

    def build_item_tab(self):
        tk.Label(
            self.item_tab,
            text="Target Mod/Keyword:"
        ).pack(anchor="w", padx=10, pady=(10, 0))

        self.item_regex_entry = tk.Entry(self.item_tab, width=60)
        self.item_regex_entry.pack(anchor="w", padx=10, pady=5)

        tk.Label(
            self.item_tab,
            text="e.g. \nof the prodigy | meteor\nincreased effect of tailwind | onslaught\n强大的|奇才之\n提速尾流|中毒\nAll Languages supported",
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=10, pady=(10, 0))

    def build_map_tab(self):
        tk.Label(
            self.map_tab,
            text="Map Avoid Regex:"
        ).pack(anchor="w", padx=10, pady=(10, 0))

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
            tk.Label(frame, text=label, width=18, anchor="w").grid(
                row=i,
                column=0,
                sticky="w",
                pady=2,
            )

            entry = tk.Entry(frame, width=12)
            entry.grid(row=i, column=1, sticky="w", pady=2)

            self.map_entries[key] = entry

        tk.Label(
            self.map_tab,
            text="Empty fields are ignored.",
        ).pack(anchor="w", padx=10, pady=(5, 0))

    def build_control_panel(self, parent):
        panel = tk.Frame(parent)
        panel.place(in_=self.notebook, x=400, y=170)

        tk.Label(panel, text="Max Attempt:").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))

        self.limit_entry = tk.Entry(panel, width=10)
        self.limit_entry.insert(0, "40")
        self.limit_entry.grid(row=0, column=1, columnspan=2, sticky="w", pady=(0, 8))

        self.currency_mode_var = tk.StringVar(value="single")

        self.single_currency_radio = tk.Radiobutton(
            panel,
            text="Chaos Orb",
            variable=self.currency_mode_var,
            value="single",
        )
        self.single_currency_radio.grid(row=1, column=0, columnspan=2, sticky="w")

        self.extra_currency_radio = tk.Radiobutton(
            panel,
            text="Alchemy&Scour",
            variable=self.currency_mode_var,
            value="extra",
        )
        self.extra_currency_radio.grid(row=2, column=0, columnspan=2, sticky="w")

        self.shortcut_label = tk.Label(panel, text="Shortcut:")
        self.shortcut_label.grid(row=3, column=0, sticky="e", pady=5)

        self.shortcut_entry = tk.Entry(panel, width=10)
        self.shortcut_entry.insert(0, "alt")
        self.shortcut_entry.grid(row=3, column=1, sticky="w", pady=5)

# Speed label (new row, left aligned)
        tk.Label(panel, text="Speed:").grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # Slider (next row, fully left aligned)
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
        self.speed_slider.grid(row=5, column=0, columnspan=2, sticky="w")

    def on_tab_changed(self, event=None):
        tab = self.notebook.index(self.notebook.select())

        if tab == 0:
            self.single_currency_radio.config(text="No Augment")
            self.extra_currency_radio.config(text="Use Augment Orb")
            self.shortcut_label.config(text="Alternate Currency input:")
            self.shortcut_entry.delete(0, tk.END)
            self.shortcut_entry.insert(0, "alt")

        else:
            self.single_currency_radio.config(text="Chaos Orb")
            self.extra_currency_radio.config(text="Chaos+Exalt Orb once")
            self.shortcut_label.config(text="Alternate Currency input:")
            self.shortcut_entry.delete(0, tk.END)
            self.shortcut_entry.insert(0, "alt")

    def register_hotkeys(self):
        keyboard.add_hotkey("f6", self.start_current_tab, suppress=False)
        keyboard.add_hotkey("f7", self.roller.stop, suppress=False)

    def get_common_settings(self):
        try:
            max_attempts = int(self.limit_entry.get())
        except ValueError:
            max_attempts = 40

        return {
            "max_attempts": max_attempts,
            "speed": self.speed_var.get(),
            "use_extra_currency": self.currency_mode_var.get() == "extra",
            "shortcut_key": self.shortcut_entry.get().strip().lower() or "alt",
        }

    def start_current_tab(self):
        tab = self.notebook.index(self.notebook.select())
        settings = self.get_common_settings()

        if tab == 0:
            settings["item_regex"] = self.item_regex_entry.get()
            self.roller.start_item_thread(settings)

        else:
            settings["map_avoid_regex"] = self.map_avoid_regex_entry.get()
            settings["map_thresholds"] = {
                key: read_int_or_none(entry.get())
                for key, entry in self.map_entries.items()
            }
            self.roller.start_map_thread(settings)