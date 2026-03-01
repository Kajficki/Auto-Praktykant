import time
import re
import logging
import traceback
import threading
import ctypes
import ctypes.wintypes
import json
from pathlib import Path
from pywinauto import Desktop

# ── configuration ─────────────────────────────────────────────────────────────

SCAN_INTERVAL = 0.6   # how often to scan windows (seconds)
COOLDOWN      = 1.5   # cooldown after handling a window (seconds)
RULES_FILE    = "rules.json"
LOG_FILE      = "autopraktykant.log"

# ── logging ───────────────────────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console      = logging.StreamHandler()
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    console.setFormatter(fmt)
    file_handler.setFormatter(fmt)
    logger = logging.getLogger("autopraktykant")
    logger.setLevel(logging.INFO)
    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger

log = setup_logging()

# ── loading rules ─────────────────────────────────────────────────────────────

def load_rules(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        rules = json.load(f)
    for i, rule in enumerate(rules):
        nr = f"Rule #{i + 1}"
        if "class" not in rule:
            raise ValueError(f"{nr}: missing required field 'class'")
        if "button" not in rule:
            raise ValueError(f"{nr}: missing required field 'button'")
        if "title" not in rule and "title_regex" not in rule:
            raise ValueError(f"{nr}: required field 'title' or 'title_regex'")
        if "title" in rule and "title_regex" in rule:
            raise ValueError(f"{nr}: use 'title' OR 'title_regex', not both")
        for field in ("title_regex", "text_regex"):
            if field in rule:
                try:
                    re.compile(rule[field])
                except re.error as e:
                    raise ValueError(f"{nr}: invalid '{field}': {e}")
    log.info(f"Loaded {len(rules)} rules from '{path}'")
    return rules

# ── helpers ───────────────────────────────────────────────────────────────────

def safe_call(fn, default=None):
    # calls fn(), returns default if an exception is raised
    try:
        return fn()
    except Exception:
        return default


def get_text_lines(win) -> list[str]:
    # collects all visible text from window controls
    lines = []
    for ctrl in win.descendants():
        txt  = safe_call(lambda c=ctrl: (c.window_text() or "").strip(), "")
        name = safe_call(lambda c=ctrl: (c.element_info.name or "").strip(), "")
        lines.append(txt or name)
    return [l for l in lines if l]


def matches_rule(win, rule: dict) -> bool:
    # checks if a window matches a rule — class, title, optional text
    if safe_call(lambda: win.class_name()) != rule.get("class"):
        return False

    title = safe_call(lambda: (win.window_text() or "").strip(), "")

    if "title" in rule:
        if title != rule["title"]:
            return False
    elif "title_regex" in rule:
        if not re.search(rule["title_regex"], title, re.IGNORECASE):
            return False
    else:
        return False

    if "text_regex" in rule:
        if not any(re.search(rule["text_regex"], l, re.IGNORECASE) for l in get_text_lines(win)):
            return False

    return True


def click_button(win, button_name: str) -> bool:
    target = button_name.lower()

    for ctrl in win.descendants():
        if safe_call(lambda c=ctrl: c.element_info.control_type) != "Button":
            continue

        txt  = safe_call(lambda c=ctrl: (c.window_text() or "").strip().lower(), "")
        name = safe_call(lambda c=ctrl: (c.element_info.name or "").strip().lower(), "")

        if txt != target and name != target:
            continue

        # try invoke — clicks without moving the mouse
        try:
            ctrl.invoke()
            log.info(f"    >>> invoke: '{button_name}'")
            return True
        except Exception:
            pass

        # fallback — click_input with cursor position restored
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        try:
            ctrl.click_input()
            log.info(f"    >>> click_input: '{button_name}'")
            return True
        except Exception:
            return False
        finally:
            ctypes.windll.user32.SetCursorPos(pt.x, pt.y)  # restore cursor regardless of outcome

    log.warning(f"    Button not found: '{button_name}'")
    return False

# ── input listener thread ─────────────────────────────────────────────────────

def watch_input(rules: list) -> None:
    # second thread — waits for commands while the main thread scans windows
    while True:
        cmd = input().strip().lower()
        if cmd == "r":
            try:
                new_rules = load_rules(RULES_FILE)
                rules.clear()
                rules.extend(new_rules)
                log.info("Rules reloaded.")
            except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
                log.error(f"Failed to reload rules: {e}")

# ── main loop ─────────────────────────────────────────────────────────────────

def monitor(rules: list[dict], total: list, by_rule: dict) -> None:
    desktop = Desktop(backend="uia")
    handled: dict[int, float] = {}

    while True:
        now     = time.time()
        handled = {h: t for h, t in handled.items() if now - t < 60}  # remove old handles

        for win in desktop.windows():
            if not safe_call(lambda w=win: w.is_visible(), False):
                continue

            handle = safe_call(lambda w=win: w.handle)
            if handle is None:
                continue

            if handle in handled and now - handled[handle] < COOLDOWN:
                continue

            for idx, rule in enumerate(rules):
                if matches_rule(win, rule):
                    title = safe_call(lambda w=win: w.window_text(), "")
                    cls   = safe_call(lambda w=win: w.class_name(), "")
                    log.info(f"[WINDOW] class={cls} | title='{title}' | rule #{idx + 1}")

                    if click_button(win, rule["button"]):
                        handled[handle] = now
                        total[0] += 1
                        by_rule[idx] = by_rule.get(idx, 0) + 1
                    break  # stop checking rules once a match is found

        time.sleep(SCAN_INTERVAL)

# ── start ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        rules = load_rules(RULES_FILE)
    except FileNotFoundError:
        log.error(f"Rules file not found: '{RULES_FILE}'")
        input("Press ENTER to close...")
        raise SystemExit(1)
    except (ValueError, json.JSONDecodeError) as e:
        log.error(f"Error in rules file: {e}")
        input("Press ENTER to close...")
        raise SystemExit(1)

    log.info("=== AUTOPRAKTYKANT STARTED ===")
    log.info(f"Log file: {Path(LOG_FILE).resolve()}")
    log.info("'r' + ENTER to reload rules | CTRL+C to quit")

    total   = [0]  # list instead of int — allows mutation inside functions
    by_rule: dict[int, int] = {}
    start   = time.time()

    # start input listener thread (daemon=True — closes with the program)
    t = threading.Thread(target=watch_input, args=(rules,), daemon=True)
    t.start()

    while True:
        try:
            monitor(rules, total, by_rule)
        except KeyboardInterrupt:
            log.info("Stopped by user.")
            uptime = int(time.time() - start)
            h, m   = divmod(uptime // 60, 60)
            log.info("=" * 50)
            log.info(f"  Uptime:          {h}h {m}min")
            log.info(f"  Windows handled: {total[0]}")
            for idx, count in sorted(by_rule.items()):
                name = rules[idx].get("title") or rules[idx].get("title_regex", f"rule #{idx+1}")
                log.info(f"  Rule #{idx + 1} ({name}): {count}x")
            log.info("=" * 50)
            break
        except Exception:
            log.error("Unexpected error — restarting in 5s:")
            log.error(traceback.format_exc())
            time.sleep(5)
            log.info("Restarting...")
