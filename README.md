# Autopraktykant — Windows Dialog Automation

A lightweight tool that runs in the background and automatically clicks dialog windows that appear during repetitive tasks — no manual intervention needed.

Companion tool **Autoinwigilator** inspects open windows and generates ready-to-use rules for Autopraktykant.

---

## Requirements

- Python 3.10+
- `pywinauto` library

Install dependencies:
```
pip install pywinauto
```

---

## Usage

**Start the automation:**
```
python autopraktykant.py
```

Press `CTRL+C` to stop. A session summary will be printed on exit.

**While running:**
- Type `r` + Enter to reload `rules.json` without restarting

---

**Inspect a new window and generate a rule:**
```
python autoinwigilator.py
```

---

## Files

| File                  | Description                                        |
|-----------------------|----------------------------------------------------|
| `autopraktykant.py`   | Main automation script                             |
| `autoinwigilator.py`  | Window inspector — generates rules interactively   |
| `rules.json`          | Rule configuration — edit this to add new windows  |
| `autopraktykant.log`  | Activity log (created automatically)               |

---

## Adding a New Rule

All rules live in `rules.json`. Each rule is an object with the following fields:

| Field         | Required | Description                                              |
|---------------|----------|----------------------------------------------------------|
| `class`       | ✅        | System window class (e.g. `"#32770"`)               |
| `button`      | ✅        | Button label to click (e.g. `"OK"`, `"Close"`)           |
| `title`       | ✅*       | Exact window title                                       |
| `title_regex` | ✅*       | Window title as a regular expression (instead of title)  |
| `text_regex`  | ❌        | Optional: text that must be visible inside the window    |

*Either `title` or `title_regex` is required — not both.

### Example — exact title match:
```json
{
    "class": "#32770",
    "title": "Confirm",
    "text_regex": "^Are you sure you want to delete",
    "button": "Yes"
},
```

### Example — regex title match:
```json
{
    "class": "#32770",
    "title_regex": "^Microsoft Office",
    "text_regex": "^Do you want to save",
    "button": "Don't Save"
}
```

### How to find the class and title of a new window

Use **Autoinwigilator** — it scans all open windows and shows their class, title, buttons and text content, then guides you through creating a rule which is saved directly to `rules.json`.

---

## Configuration (in `autopraktykant.py`)

```python
SCAN_INTERVAL = 0.6   # how often to scan for windows (seconds)
COOLDOWN      = 1.5   # cooldown after handling a window (seconds)
```

---

## Log output

Every action is logged to both the console and `autopraktykant.log`:

```
2024-03-15 09:12:44  INFO     Loaded 3 rules from 'rules.json'
2024-03-15 09:12:44  INFO     === AUTOPRAKTYKANT STARTED ===
2024-03-15 09:13:02  INFO     [WINDOW] class=#32770 | title='Confirm' | rule #1
2024-03-15 09:13:02  INFO         >>> invoke: 'Yes'
```

Session summary on exit:

```
2024-03-15 17:00:00  INFO     ==================================================
2024-03-15 17:00:00  INFO       Uptime:          7h 47min
2024-03-15 17:00:00  INFO       Windows handled: 143
2024-03-15 17:00:00  INFO       Rule #1 (Confirm): 89x
2024-03-15 17:00:00  INFO       Rule #2 (^Microsoft Office): 54x
2024-03-15 17:00:00  INFO     ==================================================
```
