import time
import json
from pywinauto import Desktop

# ── konfiguracja ──────────────────────────────────────────────────────────────

IGNORE_TITLES = {"", "Program Manager", "Windows Input Experience", "Settings"}

# ── pomocnicze ────────────────────────────────────────────────────────────────

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
    print("  Otwarte okna:")
    print("=" * 60)
    for i, w in enumerate(windows):
        btns = ", ".join(w["buttons"]) if w["buttons"] else "brak"
        print(f"  [{i}] {w['title']}")
        print(f"       class: {w['class']}  |  przyciski: {btns}")
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

# ── główna pętla ──────────────────────────────────────────────────────────────

def monitor():
    desktop = Desktop(backend="uia")

    print("=" * 60)
    print("  INSPEKTOR OKIEN — autopraktykant")
    print("=" * 60)
    print("Wpisz 's' żeby odświeżyć listę okien.")
    print("Wpisz numer okna żeby stworzyć dla niego regułę.")
    print("CTRL+C aby zakończyć.\n")

    windows = scan_windows(desktop)
    print_windows(windows)

    while True:
        cmd = input("\n  Wpisz numer okna lub 's' żeby odświeżyć: ").strip().lower()

        if cmd == "s":
            windows = scan_windows(desktop)
            print_windows(windows)
            continue

        if not cmd.isdigit() or int(cmd) >= len(windows):
            print("  Nieprawidłowy numer — spróbuj ponownie.")
            continue

        info = windows[int(cmd)]

        print(f"\n{'─' * 60}")
        print(f"  class : {info['class']}")
        print(f"  title : {info['title']}")
        if info["buttons"]:
            print(f"  przyciski: {', '.join(info['buttons'])}")
        if info["texts"]:
            print(f"  teksty w oknie:")
            for t in info["texts"]:
                print(f"    • {t}")
        print(f"{'─' * 60}\n")

        # wybór przycisku
        if info["buttons"]:
            print(f"  Dostępne przyciski: {', '.join(info['buttons'])}")
            button = input("  Który przycisk ma być kliknięty? ").strip()
        else:
            button = input("  Podaj nazwę przycisku: ").strip()

        # title jako regex?
        use_regex = input("\n  Użyć tytułu jako regex? (przyda się gdy tytuł zmienia się np. zawiera numer) [t/n]: ").strip().lower() == "t"

        # text_regex?
        text_regex = None
        if info["texts"]:
            add_text = input("\n  Dodać dopasowanie tekstu w oknie? (dla większej pewności) [t/n]: ").strip().lower()
            if add_text == "t":
                print(f"  Teksty w oknie:")
                for i, t in enumerate(info["texts"]):
                    print(f"    [{i}] {t}")
                idx = input("  Numer tekstu do użycia (lub Enter żeby wpisać własny): ").strip()
                if idx.isdigit() and int(idx) < len(info["texts"]):
                    text_regex = f"^{info['texts'][int(idx)]}"
                else:
                    text_regex = input("  Wpisz własny text_regex: ").strip() or None

        rule = build_rule(info, button, use_regex, text_regex)

        print(f"\n{'─' * 60}")
        print("  Gotowy wpis:\n")
        print("  " + json.dumps(rule, ensure_ascii=False, indent=4).replace("\n", "\n  "))
        print(f"{'─' * 60}\n")

        confirm = input("  Dodać automatycznie do rules.json? [t/n]: ").strip().lower()
        if confirm == "t":
            try:
                with open("rules.json", encoding="utf-8") as f:
                    existing = json.load(f)
                existing.append(rule)
                with open("rules.json", "w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=4)
                print("  Zapisano! Wpisz 'r' w autopraktykantcie żeby przeładować reguły.\n")
            except FileNotFoundError:
                print("  Nie znaleziono rules.json — upewnij się że plik jest w tym samym folderze.\n")
            except json.JSONDecodeError:
                print("  Błąd odczytu rules.json — plik może być uszkodzony.\n")
        else:
            print("  Pominięto.\n")

        windows = scan_windows(desktop)
        print_windows(windows)

# ── start ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        print("\nZakończono.")