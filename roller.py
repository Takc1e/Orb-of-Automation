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
    parse_map_stats,
)
from regex_utils import clean_poe_regex, compile_regex


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

    def _run_loop(self, mode: str, matcher, settings: dict):
        self.running = True

        safety_limit = settings.get("max_attempts", 40)
        speed = settings.get("speed", 1.0)
        use_extra_currency = settings.get("use_extra_currency", False)
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
