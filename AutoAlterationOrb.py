import tkinter as tk
from tkinter import scrolledtext
import keyboard
import pyautogui
import pyperclip
import time
import re
import threading
import ctypes

# ---------------- Hotkey key codes ----------------

VK_ESCAPE = 0x1B
VK_F7 = 0x76
VK_F8 = 0x77


def key_pressed(vk_code):
    return ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000


# ---------------- Speed settings ----------------

pyautogui.PAUSE = 0

COPY_DELAY = 0.015
CLICK_DELAY = 0.005
AUGMENT_DELAY = 0.02
CTRL_HOLD_DELAY = 0.005
ITERATION_DELAY = 0.02

running = False


# ---------------- Core functions ----------------

def extract_item_name(text):
    lines = text.splitlines()
    capture = False
    extracted = []

    for line in lines:
        if line.startswith("Rarity:") or line.startswith("稀有度:"):
            capture = True
            continue

        if line.strip() == "--------" and capture:
            break

        if capture:
            extracted.append(line)

    return "".join(line.lstrip() for line in extracted)


def log(message):
    output_box.insert(tk.END, message + "\n")
    output_box.see(tk.END)


def stop_script():
    global running
    running = False

    try:
        pyautogui.keyUp("shift")
        pyautogui.keyUp("ctrl")
    except:
        pass

    log("Stopped. Ready again.")


def run_script():
    global running

    if running:
        return

    user_regex = regex_entry.get().strip()

    if not user_regex:
        log("Please enter a regex first.")
        return

    try:
        compiled_regex = re.compile(user_regex, re.IGNORECASE)
    except re.error as e:
        log(f"Invalid regex: {e}")
        return

    try:
        safety_limit = int(limit_entry.get())
    except ValueError:
        safety_limit = 40

    ctrl_click_enabled = ctrl_click_var.get()

    running = True
    attempts = 0
    attempt_width = len(str(safety_limit))

    log("Started. Shift is being held automatically.")

    pyautogui.keyDown("shift")

    try:
        while running and attempts < safety_limit:

            if key_pressed(VK_ESCAPE) or key_pressed(VK_F7) or key_pressed(VK_F8):
                log("Emergency key pressed. Stopping.")
                break

            pyautogui.hotkey("ctrl", "c")
            time.sleep(COPY_DELAY)

            if key_pressed(VK_ESCAPE) or key_pressed(VK_F7) or key_pressed(VK_F8):
                log("Emergency key pressed. Stopping.")
                break

            raw_text = pyperclip.paste()
            item_name = extract_item_name(raw_text)

            matched = compiled_regex.search(raw_text)

            if matched:
                log(f"Match found: {item_name}")
                break

            log(
                f"Attempt {str(attempts + 1).rjust(attempt_width)} | "
                f"Item: {item_name}"
            )

            pyautogui.click()
            time.sleep(CLICK_DELAY)

            if ctrl_click_enabled:
                time.sleep(AUGMENT_DELAY)

                try:
                    pyautogui.keyDown("ctrl")
                    time.sleep(CTRL_HOLD_DELAY)
                    pyautogui.click()
                finally:
                    pyautogui.keyUp("ctrl")

            attempts += 1
            time.sleep(ITERATION_DELAY)

        if attempts >= safety_limit:
            log(f"Reached safety limit: {safety_limit}")

    finally:
        running = False
        pyautogui.keyUp("shift")
        pyautogui.keyUp("ctrl")
        log("Ready again. Press F6 to start.")


def start_thread():
    threading.Thread(target=run_script, daemon=True).start()


# ---------------- UI ----------------

root = tk.Tk()
root.title("AutoAlterationOrb")
root.geometry("700x470")

tk.Label(root, text="Item Regex:").pack(
    anchor="w", padx=10, pady=(10, 0)
)

regex_entry = tk.Entry(root, width=85)
regex_entry.pack(padx=10, pady=5)

tk.Label(root, text="Safety limit:").pack(anchor="w", padx=10)

limit_entry = tk.Entry(root, width=20)
limit_entry.insert(0, "40")
limit_entry.pack(anchor="w", padx=10, pady=5)

ctrl_click_var = tk.BooleanVar()

tk.Checkbutton(
    root,
    text="Always Use Augment Orb",
    variable=ctrl_click_var
).pack(anchor="w", padx=10, pady=5)

tk.Label(
    root,
    text="Hotkeys: F6 Start | F7 Stop | F8 Emergency Stop | Esc Emergency Stop"
).pack(pady=5)

output_box = scrolledtext.ScrolledText(root, width=85, height=20)
output_box.pack(padx=10, pady=10)

log("Ready. Enter regex, set mode, then use F6 in game.")

# ---------------- Global hotkeys ----------------

keyboard.add_hotkey("f6", start_thread, suppress=False)
keyboard.add_hotkey("f7", stop_script, suppress=False)
keyboard.add_hotkey("f8", stop_script, suppress=False)

root.mainloop()