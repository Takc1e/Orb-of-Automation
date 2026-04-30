# Auto-alteration-Orb
Orb of Alteration automation tool for Path of Exile 1  
Reads item data from the clipboard (Ctrl + C) instead of game files which is not against GGG T&C :)   



# Requirements

Python 3.8+
Windows OS (uses WinAPI for key detection)

Install dependencies:
```bash
pip install pyautogui keyboard pyperclip
```



# Useage 
1. Run the script:
```bash
python AutoAlterationOrb.py
```

2. Key in item regex ( same format in POE, Supports all languages) and set up accordingly
![alt text](Demo.png)

3. Rightclick Orb of Alteration and hover on the item
![alt text](Hoverdemo.png)

4. Press F6 to start until getting the desired modifier

# Notes

- Works by reading clipboard text (Ctrl + C) and PyAutoGUI lib for mouse and keyboard actions  
- No direct interaction with game files  
- Adjust speed if rolls become unstable     

--------------------------------------------------

# Disclaimer

Use at your own risk.
