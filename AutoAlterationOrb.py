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

VK_F7 = 0x76


def key_pressed(vk_code):
    return ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000


# ---------------- Speed settings ----------------

pyautogui.PAUSE = 0

COPY_DELAY = 0.03
CLICK_DELAY = 0.01
AUGMENT_DELAY = 0.03
CTRL_HOLD_DELAY = 0.008
ITERATION_DELAY = 0.04

running = False


# ---------------- Core functions ----------------


def extract_item_name(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        # First colon line is usually "Rarity:", "稀 有 度:", etc.
        if ":" in line or "：" in line:
            name_lines = []

            for j in range(i + 1, len(lines)):
                if lines[j] == "--------":
                    break
                name_lines.append(lines[j])

            return " ".join(name_lines)

    return ""


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
    
    augment_key = augment_key_entry.get().strip().lower()

    if not augment_key:
        augment_key = "alt"
    
    speed = speed_var.get()
    copy_delay = COPY_DELAY / speed
    click_delay = CLICK_DELAY / speed
    augment_delay = AUGMENT_DELAY / speed
    ctrl_hold_delay = CTRL_HOLD_DELAY / speed
    iteration_delay = ITERATION_DELAY / speed

    running = True
    attempts = 0
    attempt_width = len(str(safety_limit))

    log("Started. Shift is being held automatically.")

    pyautogui.keyDown("shift")

    try:
        while running and attempts < safety_limit:

            if key_pressed(VK_F7) :
                log("Emergency key pressed. Stopping.")
                break

            pyautogui.hotkey("ctrl", "c")
            time.sleep(copy_delay)

            if  key_pressed(VK_F7) :
                log("Emergency key pressed. Stopping.")
                break

            raw_text = pyperclip.paste()
            raw_text = raw_text.replace("：", ":")
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
            time.sleep(click_delay)

            if ctrl_click_enabled:
                time.sleep(augment_delay)

                try:
                    pyautogui.keyDown(augment_key)
                    time.sleep(ctrl_hold_delay)
                    pyautogui.click()
                finally:
                    pyautogui.keyUp(augment_key)

            attempts += 1
            time.sleep(iteration_delay)

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

#-----------------------------------
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
#--------------------------------------------------------------------
augment_frame = tk.Frame(root)
augment_frame.pack(anchor="w", padx=10, pady=5)

tk.Checkbutton(
    augment_frame,
    text="Always Use Augment Orb",
    variable=ctrl_click_var
).pack(side="left")

tk.Label(augment_frame, text="Alternative Currency shortcut:").pack(side="left", padx=(15, 5))

augment_key_entry = tk.Entry(augment_frame, width=10)
augment_key_entry.insert(0, "alt")
augment_key_entry.pack(side="left")
#-----------------------------------
speed_var = tk.DoubleVar(value=1.0)

tk.Label(root, text="Speed multiplier:").pack(anchor="w", padx=10)

speed_slider = tk.Scale(
    root,
    from_=0.5,
    to=2.0,
    resolution=0.1,
    orient="horizontal",
    variable=speed_var,
    length=300
)
speed_slider.pack(anchor="w", padx=10, pady=5)
#------------------------------------------
tk.Label(
    root,
    text="Hotkeys: F6 Start | F7 Stop "
).pack(pady=5)

output_box = scrolledtext.ScrolledText(root, width=85, height=20)
output_box.pack(padx=10, pady=10)

log("Ready. Enter regex, set mode, then use F6 in game.")


# ---------------- Global hotkeys ----------------

keyboard.add_hotkey("f6", start_thread, suppress=False)
keyboard.add_hotkey("f7", stop_script, suppress=False)

root.mainloop()