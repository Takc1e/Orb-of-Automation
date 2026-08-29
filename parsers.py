import re


def normalize_text(text: str) -> str:
    """
    Normalize copied item text while preserving newlines.
    Important: do not remove newlines, because PoE-style regex may use $.
    """
    return text.replace("：", ":")


def extract_item_name(text: str) -> str:
    """
    Language-independent item name extraction.
    It looks for the first colon line, usually:
        Rarity:
        稀 有 度:
        Rareté:
    Then captures lines until the first separator.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if ":" in line:
            name_lines = []

            for j in range(i + 1, len(lines)):
                if lines[j] == "--------":
                    break
                name_lines.append(lines[j])

            return " ".join(name_lines)

    return ""


def parse_item_mod_lines(text: str) -> list:
    """
    Best-effort parser for explicit copied item mods.

    It ignores item metadata, requirements, enchant lines, and reminder text.
    Cluster jewel explicit mods may be copied as plain stat lines or as
    Ctrl+Alt+C modifier-detail rows like:
        { Fractured Prefix Modifier "Powerful" (Tier: 1) }
    Preserving the original line is more useful than trying to classify
    prefix/suffix here.
    """
    ignored_prefixes = (
        "物品类别",
        "物品類別",
        "稀 有 度",
        "需求",
        "等级",
        "等級",
        "物品等级",
        "物品等級",
        "Item Class",
        "Rarity",
        "Requirements",
        "Level",
        "Item Level",
    )
    ignored_exact = {
        "--------",
        "分裂之物",
        "Fractured Item",
    }
    description_markers = (
        "放入天赋树",
        "放入天賦樹",
        "可以右键点击",
        "可以右鍵點擊",
        "Place into an allocated",
        "Right click to remove",
    )

    item_name = extract_item_name(text)
    mod_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        line_without_markdown = line.lstrip("#").strip()

        if not line:
            continue

        if re.fullmatch(r"-{2,}", line):
            continue

        if line == item_name or line_without_markdown == item_name:
            continue

        if line in ignored_exact or line_without_markdown in ignored_exact:
            continue

        if line.startswith(ignored_prefixes) or line_without_markdown.startswith(ignored_prefixes):
            continue

        if any(marker in line for marker in description_markers):
            continue

        if "(enchant)" in line.lower():
            continue

        looks_like_mod = (
            line.startswith("{")
            or "+" in line
            or "%" in line
            or "(fractured)" in line.lower()
            or "Modifier" in line
            or "属性" in line
            or "屬性" in line
            or re.search(r"\d", line)
        )

        if looks_like_mod:
            mod_lines.append(line)

    return mod_lines


def extract_value(pattern: str, text: str) -> int:
    match = re.search(pattern, text, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def parse_map_stats(text):
    text = text.replace("：", ":")

    return {
        "quantity": extract_value(
            r"(?:Item Quantity|物品数量|物品數量):\s*\+(\d+)%", text
        ),

        "rarity": extract_value(
            r"(?:Item Rarity|物品稀有度):\s*\+(\d+)%", text
        ),

        "pack_size": extract_value(
            r"(?:Monster Pack Size|怪物群大小):\s*\+(\d+)%", text
        ),

        "more_maps": extract_value(
            r"(?:More Maps|更多地图|更多地圖):\s*\+(\d+)%", text
        ),

        "currency": extract_value(
            r"(?:More Currency|更多通货|更多通貨):\s*\+(\d+)%", text
        ),

        "scarabs": extract_value(
            r"(?:More Scarabs|更多圣甲虫|更多聖甲蟲):\s*\+(\d+)%", text
        ),

        "divination": extract_value(
            r"(?:More Divination Cards|更多命运卡|更多命运卡牌|命運卡增加):\s*\+(\d+)%", text
        ),
    }


def read_int_or_none(value: str):
    value = value.strip()
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def map_passes_thresholds(stats: dict, thresholds: dict) -> bool:
    """
    Current logic:
    - Empty input means ignore that field.
    - If any filled threshold is reached, the map passes.
    - If no thresholds are filled, it does not pass.
    """
    has_any_threshold = False

    for key, required in thresholds.items():
        if required is None:
            continue

        has_any_threshold = True

        if stats.get(key, 0) >= required:
            return True

    return False if has_any_threshold else False
