# Orb of Automation
Orb of Alteration automation tool for Path of Exile 1  
Reads item data from the clipboard (Ctrl + C) instead of game files which is not against GGG T&C :)   

# Useage 
1. Run **Orb of Automation.exe** as **Administrator** (Important)

  or if using python 3.8+: 
  Install dependencies:
```bash
pip install pyautogui keyboard pyperclip
```
Then Run the script:
```bash
python OrbOfAutomation.py
```

2. Key in item regex ( same format in POE, Supports all languages) and set up accordingly
![alt text](Demo_item.png)

3. Rightclick Orb of Alteration and hover on the item
![alt text](Hoverdemo.png)

4. Press F6 to start until getting the desired modifier

# Notes

- Works by reading clipboard text (Ctrl + C) and PyAutoGUI lib for mouse and keyboard actions  
- No direct interaction with game files  
- Adjust speed if rolls become unstable     

--------------------------------------------------
# Map roller (EN/简中/繁中)
1. Generate your regex from thirdparty websites(clean,unwanted mods only)
2. Key in regex and target Quantities
3. Right click chaos and hover on map, F6 to reroll
![alt text](Demo_map.png)

# Disclaimer

Not sure if GGG can detect such "unusual" currency spamming. Use at your own risk.
