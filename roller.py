import ctypes
import threading
import time

import keyboard
import pyautogui
import pyperclip

from parsers import (
    extract_item_name,
    map_passes_thresholds,
    normalize_text,
    parse_item_mod_lines,
    parse_map_stats,
)
from regex_utils import clean_poe_regex, compile_regex


VK_SHIFT = 0x10
VK_F7 = 0x76

pyautogui.PAUSE = 0


class Roller:
    def __init__(self, log_callback):
        self.running = False
        self.log = log_callback

        self.copy_delay_base = 0.12
        self.click_delay_base = 0.03
        self.augment_delay_base = 0.04
        self.shortcut_hold_delay_base = 0.03
        self.iteration_delay_base = 0.08

    def key_pressed(self, vk_code):
        return ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000

    def stop(self):
        self.running = False

        try:
            pyautogui.keyUp("shift")
            pyautogui.keyUp("ctrl")
            pyautogui.keyUp("alt")
        except Exception:
            pass

        self.log("Stopped. Ready again.")

    def start_item_thread(self, settings: dict):
        threading.Thread(target=self.run_item_mode, args=(settings,), daemon=True).start()

    def start_map_thread(self, settings: dict):
        threading.Thread(target=self.run_map_mode, args=(settings,), daemon=True).start()

    def start_cluster_thread(self, settings: dict):
        threading.Thread(target=self.run_cluster_mode, args=(settings,), daemon=True).start()

    def get_delays(self, speed: float):
        if speed <= 0:
            speed = 1.0

        return {
            "copy": self.copy_delay_base / speed,
            "click": self.click_delay_base / speed,
            "augment": self.augment_delay_base / speed,
            "shortcut_hold": self.shortcut_hold_delay_base / speed,
            "iteration": self.iteration_delay_base / speed,
        }

    def copy_item_text(self, copy_delay: float) -> str:
        time.sleep(0.03)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(copy_delay)

        raw_text = pyperclip.paste()
        return normalize_text(raw_text)

    def copy_cluster_item_text(self, copy_delay: float) -> str:
        shift_was_down = bool(self.key_pressed(VK_SHIFT))

        try:
            pyautogui.keyUp("shift")
            time.sleep(0.03)
            pyautogui.hotkey("ctrl", "alt", "c")
            time.sleep(copy_delay)
        finally:
            if shift_was_down:
                pyautogui.keyDown("shift")

        raw_text = pyperclip.paste()
        return normalize_text(raw_text)

    def click_currency(self, use_extra_currency: bool, shortcut_key: str, delays: dict):
        pyautogui.click()
        time.sleep(delays["click"])

        if use_extra_currency:
            time.sleep(delays["augment"])

            try:
                pyautogui.keyDown(shortcut_key)
                time.sleep(delays["shortcut_hold"])
                pyautogui.click()
            finally:
                pyautogui.keyUp(shortcut_key)

    def click_map_currency(self, currency_mode: str, shortcut_key: str, delays: dict):
        if currency_mode == "alch_scour":
            self.log("Using Orb of Scouring, then Orb of Alchemy.")
            try:
                pyautogui.keyDown(shortcut_key)
                time.sleep(delays["shortcut_hold"])
                pyautogui.click()
                time.sleep(delays["click"])
            finally:
                pyautogui.keyUp(shortcut_key)

            time.sleep(delays["augment"])
            pyautogui.click()
            time.sleep(delays["click"])
            return

        self.click_currency(currency_mode == "extra", shortcut_key, delays)

    def click_currency_action(
        self,
        action_name: str,
        shortcut_key: str,
        delays: dict,
        settings: dict = None,
        position_key: str = None,
        hold_shift_on_apply: bool = False,
    ):
        shortcut_key = shortcut_key.strip().lower()
        self.log(f"Using {action_name}.")

        if settings and position_key:
            item_position = settings.get("item_position")
            currency_positions = settings.get("currency_positions", {})
            currency_position = currency_positions.get(position_key)

            if item_position and currency_position:
                self.log(
                    f"{action_name}: right-click {currency_position[0]}, {currency_position[1]} "
                    f"then left-click item {item_position[0]}, {item_position[1]}."
                )

                try:
                    if hold_shift_on_apply:
                        pyautogui.keyDown("shift")
                    else:
                        pyautogui.keyUp("shift")

                    pyautogui.moveTo(currency_position[0], currency_position[1])
                    time.sleep(delays["click"])
                    pyautogui.rightClick()
                    time.sleep(delays["click"])
                    pyautogui.moveTo(item_position[0], item_position[1])
                    time.sleep(delays["click"])
                    pyautogui.leftClick()
                    time.sleep(delays["click"])
                finally:
                    if hold_shift_on_apply:
                        pyautogui.keyDown("shift")
                    else:
                        pyautogui.keyUp("shift")
                return

            self.log(
                f"Missing captured position for {action_name} or Jewel / Item. "
                "Capture all required cluster positions first."
            )
            self.running = False
            return

        if not shortcut_key:
            pyautogui.click()
            time.sleep(delays["click"])
            return

        try:
            pyautogui.keyDown(shortcut_key)
            time.sleep(delays["shortcut_hold"])
            pyautogui.click()
            time.sleep(delays["click"])
        finally:
            pyautogui.keyUp(shortcut_key)

    def click_cluster_alteration(self, delays: dict):
        self.log("Using Orb of Alteration on hovered item.")
        try:
            pyautogui.keyDown("shift")
            pyautogui.click()
            time.sleep(delays["click"])
        finally:
            pyautogui.keyDown("shift")

    def click_cluster_augment(self, shortcut_key: str, delays: dict):
        shortcut_key = shortcut_key.strip().lower() or "alt"
        self.log(f"Using Orb of Augmentation with {shortcut_key}.")

        try:
            pyautogui.keyDown("shift")
            pyautogui.keyDown(shortcut_key)
            time.sleep(delays["shortcut_hold"])
            pyautogui.click()
            time.sleep(delays["click"])
        finally:
            pyautogui.keyUp(shortcut_key)
            pyautogui.keyDown("shift")

    def run_item_mode(self, settings: dict):
        if self.running:
            return

        try:
            item_regex = compile_regex(settings["item_regex"], "item regex")
        except ValueError as e:
            self.log(str(e))
            return

        if item_regex is None:
            self.log("Please enter an item regex first.")
            return

        self._run_loop(
            mode="item",
            matcher=item_regex,
            settings=settings,
        )

    def run_map_mode(self, settings: dict):
        if self.running:
            return

        avoid_text = clean_poe_regex(settings.get("map_avoid_regex", ""))

        try:
            avoid_regex = compile_regex(avoid_text, "map avoid regex")
        except ValueError as e:
            self.log(str(e))
            return

        self._run_loop(
            mode="map",
            matcher=avoid_regex,
            settings=settings,
        )

    def run_cluster_mode(self, settings: dict):
        if self.running:
            return

        target_texts = [
            text.strip()
            for text in settings.get("cluster_targets", [])
            if text.strip()
        ]

        if len(target_texts) != 4:
            self.log("Please enter exactly 4 target mods for cluster crafting.")
            return

        try:
            target_regexes = [
                compile_regex(target_text, f"target mod {index + 1}")
                for index, target_text in enumerate(target_texts)
            ]

            for index, target_regex in enumerate(target_regexes):
                self.log(
                    f"Target {index + 1}: {target_texts[index]} -> {target_regex.pattern}"
                )

            fractured_regex = None
            if settings.get("is_fractured"):
                fractured_text = settings.get("fractured_mod", "").strip()

                if not fractured_text:
                    self.log("Please enter the fractured mod name, or untick fractured item.")
                    return

                fractured_regex = compile_regex(fractured_text, "fractured mod")

        except ValueError as e:
            self.log(str(e))
            return

        self._run_cluster_loop(target_regexes, fractured_regex, settings)

    def _run_loop(self, mode: str, matcher, settings: dict):
        self.running = True

        safety_limit = settings.get("max_attempts", 40)
        speed = settings.get("speed", 1.0)
        use_extra_currency = settings.get("use_extra_currency", False)
        currency_mode = settings.get("currency_mode", "extra" if use_extra_currency else "single")
        shortcut_key = settings.get("shortcut_key", "alt").strip().lower() or "alt"

        delays = self.get_delays(speed)

        attempts = 0
        attempt_width = len(str(safety_limit))
        
        pyautogui.keyUp("shift")
        pyautogui.keyUp("ctrl")
        pyautogui.keyUp("alt")
        time.sleep(0.05)

        self.log(f"Started {mode.upper()} mode. Shift is being held automatically.")
        pyautogui.keyDown("shift")

        try:
            while self.running and attempts < safety_limit:
                if self.key_pressed(VK_F7):
                    self.log("F7 pressed. Stopping.")
                    break

                raw_text = self.copy_item_text(delays["copy"])

                if self.key_pressed(VK_F7):
                    self.log("F7 pressed. Stopping.")
                    break

                item_name = extract_item_name(raw_text)

                if mode == "item":
                    matched = matcher.search(raw_text)

                    if matched:
                        self.log(f"Match found: {item_name}")
                        break

                elif mode == "map":
                    avoid_matched = matcher.search(raw_text) if matcher else False
                    stats = parse_map_stats(raw_text)

                    if avoid_matched:
                        self.log(
                            f"Attempt {str(attempts + 1).rjust(attempt_width)} | "
                            f"Rejected bad mod | {item_name}"
                        )
                    elif map_passes_thresholds(stats, settings["map_thresholds"]):
                        self.log(
                            f"Map match found: {item_name} | "
                            f"Qty {stats['quantity']} | Pack {stats['pack_size']} | "
                            f"Currency {stats['currency']} | Scarabs {stats['scarabs']} | "
                            f"Div {stats['divination']}"
                        )
                        break
                    else:
                        self.log(
                            f"Attempt {str(attempts + 1).rjust(attempt_width)} | "
                            f"Qty {stats['quantity']} | Pack {stats['pack_size']} | "
                            f"Currency {stats['currency']} | Scarabs {stats['scarabs']} | "
                            f"Div {stats['divination']}"
                        )

                if mode == "map":
                    self.click_map_currency(currency_mode, shortcut_key, delays)
                else:
                    self.click_currency(use_extra_currency, shortcut_key, delays)

                attempts += 1
                time.sleep(delays["iteration"])

            if attempts >= safety_limit:
                self.log(f"Reached max attempt: {safety_limit}")

        finally:
            self.running = False
            pyautogui.keyUp("shift")
            pyautogui.keyUp("ctrl")
            pyautogui.keyUp("alt")
            self.log("Ready again. Press F6 to start.")

    def _count_cluster_targets(self, text: str, target_regexes: list) -> int:
        return len(self._get_cluster_target_matches(text, target_regexes))

    def _get_cluster_target_matches(self, text: str, target_regexes: list) -> list:
        return [
            index + 1
            for index, target_regex in enumerate(target_regexes)
            if target_regex.search(text)
        ]

    def _get_unwanted_cluster_mods(self, mod_lines: list, target_regexes: list) -> list:
        unwanted_lines = []

        for line in mod_lines:
            if not any(target_regex.search(line) for target_regex in target_regexes):
                unwanted_lines.append(line)

        return unwanted_lines

    def _cluster_reset(self, settings: dict, delays: dict):
        self.log("Resetting with Scour + Transmute.")
        self.click_currency_action(
            "Orb of Scouring",
            settings["scour_key"],
            delays,
            settings,
            "scour",
        )
        time.sleep(delays["iteration"])
        self.click_currency_action(
            "Orb of Transmutation",
            settings["transmute_key"],
            delays,
            settings,
            "transmute",
        )
        time.sleep(delays["iteration"])

    def _cluster_reselect_alteration(self, settings: dict, delays: dict):
        self.log("Selecting Orb of Alteration and holding Shift for repeat use.")
        self.click_currency_action(
            "Orb of Alteration",
            settings["alteration_key"],
            delays,
            settings,
            "alteration",
            hold_shift_on_apply=True,
        )
        time.sleep(delays["iteration"])

    def _run_cluster_loop(self, target_regexes: list, fractured_regex, settings: dict):
        self.running = True

        safety_limit = settings.get("max_attempts", 40)
        speed = settings.get("speed", 1.0)
        use_augment = settings.get("use_extra_currency", False)
        protected_target_floor = 1 if settings.get("is_fractured") else 0
        stop_target_count = 3 if settings.get("stop_at_three_targets") else 4
        delays = self.get_delays(speed)

        attempts = 0
        stage = "alter"
        target_count_before_currency = 0
        target_matches_before_currency = set()
        fractured_warning_logged = False
        attempt_width = len(str(safety_limit))

        pyautogui.keyUp("shift")
        pyautogui.keyUp("ctrl")
        pyautogui.keyUp("alt")
        time.sleep(0.05)

        self.log("Started CLUSTER mode. Shift is being held automatically.")
        pyautogui.keyDown("shift")
        self._cluster_reselect_alteration(settings, delays)

        try:
            while self.running and attempts < safety_limit:
                if self.key_pressed(VK_F7):
                    self.log("F7 pressed. Stopping.")
                    break

                if settings.get("item_position"):
                    pyautogui.moveTo(
                        settings["item_position"][0],
                        settings["item_position"][1],
                    )

                raw_text = self.copy_item_text(delays["copy"])

                if self.key_pressed(VK_F7):
                    self.log("F7 pressed. Stopping.")
                    break

                item_name = extract_item_name(raw_text)
                matched_targets = self._get_cluster_target_matches(raw_text, target_regexes)
                target_count = len(matched_targets)
                mod_lines = parse_item_mod_lines(raw_text)
                unwanted_mods = self._get_unwanted_cluster_mods(mod_lines, target_regexes)

                if (
                    fractured_regex
                    and not fractured_regex.search(raw_text)
                    and not fractured_warning_logged
                ):
                    self.log(
                        "Warning: fractured mod text was not detected in copied item text. "
                        "Continuing because target mods are still counted from clipboard text."
                    )
                    fractured_warning_logged = True

                self.log(
                    f"Attempt {str(attempts + 1).rjust(attempt_width)} | "
                    f"{stage.upper()} | Mods {len(mod_lines)} | "
                    f"Targets {target_count}/4 {matched_targets} | "
                    f"Unwanted {len(unwanted_mods)} | {item_name}"
                )

                if unwanted_mods and stage != "alter":
                    self.log("Unwanted mods: " + " | ".join(unwanted_mods[:3]))

                if target_count >= stop_target_count:
                    self.log(
                        f"Cluster craft complete at {target_count}/4 targets: {item_name}"
                    )
                    break

                if stage == "alter":
                    if target_count >= 2:
                        target_count_before_currency = target_count
                        target_matches_before_currency = set(matched_targets)
                        self.click_currency_action(
                            "Regal Orb",
                            settings["regal_key"],
                            delays,
                            settings,
                            "regal",
                        )
                        stage = "check_regal"
                    elif target_count == 1 and use_augment:
                        target_count_before_currency = target_count
                        target_matches_before_currency = set(matched_targets)
                        self.click_cluster_augment(settings["shortcut_key"], delays)
                        stage = "check_augment"
                    else:
                        self.click_cluster_alteration(delays)

                elif stage == "check_augment":
                    added_targets = set(matched_targets) - target_matches_before_currency

                    if added_targets:
                        target_count_before_currency = target_count
                        target_matches_before_currency = set(matched_targets)
                        self.click_currency_action(
                            "Regal Orb",
                            settings["regal_key"],
                            delays,
                            settings,
                            "regal",
                        )
                        stage = "check_regal"
                    else:
                        self.log(
                            "Augment did not add a wanted mod. "
                            f"Before {target_count_before_currency}/4, now {target_count}/4 "
                            f"{matched_targets}. Rolling again with Alteration."
                        )
                        self.click_cluster_alteration(delays)
                        stage = "alter"

                elif stage == "check_regal":
                    added_targets = set(matched_targets) - target_matches_before_currency

                    if added_targets:
                        target_count_before_currency = target_count
                        target_matches_before_currency = set(matched_targets)
                        self.click_currency_action(
                            "Exalted Orb",
                            settings["exalt_key"],
                            delays,
                            settings,
                            "exalt",
                        )
                        stage = "check_exalt"
                    else:
                        self.log("Regal added an unwanted mod. Using Annul before Exalt.")
                        target_count_before_currency = target_count
                        target_matches_before_currency = set(matched_targets)
                        self.click_currency_action(
                            "Orb of Annulment",
                            settings["annul_key"],
                            delays,
                            settings,
                            "annul",
                        )
                        stage = "check_exalt_annul"

                elif stage == "check_exalt":
                    if target_count >= stop_target_count:
                        self.log(
                            f"Cluster craft complete at {target_count}/4 targets: {item_name}"
                        )
                        break

                    added_targets = set(matched_targets) - target_matches_before_currency

                    if added_targets:
                        target_count_before_currency = target_count
                        target_matches_before_currency = set(matched_targets)
                        self.click_currency_action(
                            "Exalted Orb",
                            settings["exalt_key"],
                            delays,
                            settings,
                            "exalt",
                        )
                    else:
                        target_count_before_currency = target_count
                        target_matches_before_currency = set(matched_targets)
                        self.click_currency_action(
                            "Orb of Annulment",
                            settings["annul_key"],
                            delays,
                            settings,
                            "annul",
                        )
                        stage = "check_exalt_annul"

                elif stage == "check_exalt_annul":
                    lost_targets = target_matches_before_currency - set(matched_targets)

                    if lost_targets:
                        if target_count <= protected_target_floor:
                            self.log("Annul removed all removable wanted mods during salvage.")
                            self._cluster_reset(settings, delays)
                            self._cluster_reselect_alteration(settings, delays)
                            stage = "alter"
                        else:
                            self.log(
                                "Annul removed a wanted mod, but useful targets remain. "
                                "Trying Annul again."
                            )
                            target_count_before_currency = target_count
                            target_matches_before_currency = set(matched_targets)
                            self.click_currency_action(
                                "Orb of Annulment",
                                settings["annul_key"],
                                delays,
                                settings,
                                "annul",
                            )
                    else:
                        target_count_before_currency = target_count
                        target_matches_before_currency = set(matched_targets)
                        self.click_currency_action(
                            "Exalted Orb",
                            settings["exalt_key"],
                            delays,
                            settings,
                            "exalt",
                        )
                        stage = "check_exalt"

                attempts += 1
                time.sleep(delays["iteration"])

            if attempts >= safety_limit:
                self.log(f"Reached max attempt: {safety_limit}")

        finally:
            self.running = False
            pyautogui.keyUp("shift")
            pyautogui.keyUp("ctrl")
            pyautogui.keyUp("alt")
            self.log("Ready again. Press F6 to start.")
