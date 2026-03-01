import time
import json
from pywinauto import Desktop

# ── configuration ─────────────────────────────────────────────────────────────

IGNORE_TITLES = {"", "Program Manager", "Windows Input Experience", "Settings"}

# ── helpers ───────────────────────────────────────────────────────────────────

def safe_call(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def get_buttons(win) -> list[str]:
    buttons = []
    for ctrl in win.descendants():
        if safe_call(lambda c=ctrl: c.element_info.control_type) != "Button":
            continue
        txt  = safe_call(lambda c=ctrl: (c.window_text() or "").strip(), "")
        name = safe_call(lambda c=ctrl: (c.element_info.name or "").strip(), "")
        label = txt or name
        if label:
            buttons.append(label)
    return buttons


def get_text_lines(win) -> list[str]:
    lines = []
    for ctrl in win.descendants():
        txt  = safe_call(lambda c=ctrl: (c.window_text() or "").strip(), "")
        name = safe_call(lambda c=ctrl: (c.element_info.name or "").strip(), "")
        label = txt or name
        if label:
            lines.append(label)
    return list(dict.fromkeys(lines))[:8]


def scan_windows(desktop) -> list[dict]:
    results = []
    for win in desktop.windows():
        if not safe_call(lambda w=win: w.is_visible(), False):
            continue
        title = safe_call(lambda w=win: (w.window_text() or "").strip(), "")
        cls   = safe_call(lambda w=win: w.class_name(), "")
        if not title or not cls or title in IGNORE_TITLES:
            continue
        results.append({
            "handle":  safe_call(lambda w=win: w.handle),
            "class":   cls,
            "title":   title,
            "buttons": get_buttons(win),
            "texts":   get_text_lines(win),
            "_win":    win,
        })
    return results


def print_windows(windows: list[dict]) -> None:
    print("\n" + "=" * 60)
    print("  Open windows:")
    print("=" * 60)
    for i, w in enumerate(windows):
        btns = ", ".join(w["buttons"]) if w["buttons"] else "none"
        print(f"  [{i}] {w['title']}")
        print(f"       class: {w['class']}  |  buttons: {btns}")
    print("=" * 60)


def build_rule(info: dict, button: str, use_regex: bool, text_regex: str | None) -> dict:
    rule = {"class": info["class"]}
    if use_regex:
        rule["title_regex"] = f"^{info['title']}"
    else:
        rule["title"] = info["title"]
    if text_regex:
        rule["text_regex"] = text_regex
    rule["button"] = button
    return rule

# ── main loop ─────────────────────────────────────────────────────────────────

def monitor():
    desktop = Desktop(backend="uia")

    print("=" * 60)
    print("  AUTOINWIGILATOR — window inspector")
    print("=" * 60)
    print("Type 's' to refresh the window list.")
    print("Type a window number to create a rule for it.")
    print("CTRL+C to quit.\n")

    windows = scan_windows(desktop)
    print_windows(windows)

    while True:
        cmd = input("\n  Enter window number or 's' to refresh: ").strip().lower()

        if cmd == "s":
            windows = scan_windows(desktop)
            print_windows(windows)
            continue

        if not cmd.isdigit() or int(cmd) >= len(windows):
            print("  Invalid number — try again.")
            continue

        info = windows[int(cmd)]

        print(f"\n{'─' * 60}")
        print(f"  class  : {info['class']}")
        print(f"  title  : {info['title']}")
        if info["buttons"]:
            print(f"  buttons: {', '.join(info['buttons'])}")
        if info["texts"]:
            print(f"  text inside window:")
            for t in info["texts"]:
                print(f"    • {t}")
        print(f"{'─' * 60}\n")

        # button selection
        if info["buttons"]:
            print(f"  Available buttons: {', '.join(info['buttons'])}")
            button = input("  Which button should be clicked? ").strip()
        else:
            button = input("  Enter button name: ").strip()

        # title as regex?
        use_regex = input("\n  Use title as regex? (useful if title changes e.g. contains a number) [y/n]: ").strip().lower() == "y"

        # text_regex?
        text_regex = None
        if info["texts"]:
            add_text = input("\n  Add text matching for extra safety? [y/n]: ").strip().lower()
            if add_text == "y":
                print(f"  Text inside window:")
                for i, t in enumerate(info["texts"]):
                    print(f"    [{i}] {t}")
                idx = input("  Text number to use (or Enter to type your own): ").strip()
                if idx.isdigit() and int(idx) < len(info["texts"]):
                    text_regex = f"^{info['texts'][int(idx)]}"
                else:
                    text_regex = input("  Enter custom text_regex: ").strip() or None

        rule = build_rule(info, button, use_regex, text_regex)

        print(f"\n{'─' * 60}")
        print("  Generated rule:\n")
        print("  " + json.dumps(rule, ensure_ascii=False, indent=4).replace("\n", "\n  "))
        print(f"{'─' * 60}\n")

        confirm = input("  Add automatically to rules.json? [y/n]: ").strip().lower()
        if confirm == "y":
            try:
                with open("rules.json", encoding="utf-8") as f:
                    existing = json.load(f)
                existing.append(rule)
                with open("rules.json", "w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=4)
                print("  Saved! Type 'r' in autopraktykant to reload rules.\n")
            except FileNotFoundError:
                print("  rules.json not found — make sure it's in the same folder.\n")
            except json.JSONDecodeError:
                print("  Error reading rules.json — file may be corrupted.\n")
        else:
            print("  Skipped.\n")

        windows = scan_windows(desktop)
        print_windows(windows)

# ── start ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        print("\nDone.")
