#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Usage:
  python keet.py calibrate    calibrate mode (set input and ocr_box)
  python keet.py run          run checking

Default:
 - Generates usernames of length 3 (changeable via --min-len/--max-len)
 - Condition: at least one digit (can disable with --no-require-digit)
 - All checked usernames are stored in checked_nicks.txt and skipped on rerun
 - Free usernames are stored in free_nicks.txt (no duplicates)

 Использование:
  python keet.py calibrate         режим калибровки (выставить input и ocr_box)
  python keet.py run               запуск перебора

По умолчанию:
 - Генерируются ники длиной 3 символа (можно менять --min-len/--max-len)
 - Условие: минимум одна цифра (можно отключить --no-require-digit)
 - Все проверенные ники сохраняются в checked_nicks.txt и при повторном запуске пропускаются
 - Свободные ники добавляются в free_nicks.txt (без дублей)
"""

import argparse
import itertools
import json
import string
import time
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
import pyautogui
import pytesseract
from PIL import Image
from pywinauto import findwindows, Application

LANGS = {
    "ru": {
        "calibrator_title": "=== Калибратор ===",
        "calibrator_step1": "1) Сделай видимым поле ввода в приложении.",
        "calibrator_step2": "2) Наведи курсор на поле ввода и нажми Enter в этой консоли...",
        "calibrator_step3": "3) Наведи курсор на ЛЕВЫЙ ВЕРХНИЙ угол области статуса и нажми Enter...",
        "calibrator_step4": "4) Наведи курсор на ПРАВЫЙ НИЖНИЙ угол области статуса и нажми Enter...",
        "calibration_done": "Калибровка завершена.",
        "ocr_sample": "OCR результат:",
        "focus_fail": "Не удалось найти окно — фокус через клик в INPUT_CLICK:",
        "checking": "Проверяю",
        "used": "Занят ❌",
        "free": "Свободен ✅",
        "free_already": "Свободен ✅ (уже в файле)",
        "free_saved": "Свободен ✅ (записываю)",
        "unknown": "Неопределённо",
        "interrupted": "Прервано пользователем (Ctrl+C).",
        "done": "Работа завершена.",
        "ocr_checking": "checking",
        "ocr_used": "already in use",
        "ocr_free": "available",
    },
    "en": {
        "calibrator_title": "=== Calibrator ===",
        "calibrator_step1": "1) Make the input field visible in the app.",
        "calibrator_step2": "2) Hover the mouse over the input field and press Enter in this console...",
        "calibrator_step3": "3) Hover the mouse over the TOP LEFT corner of the status area and press Enter...",
        "calibrator_step4": "4) Hover the mouse over the BOTTOM RIGHT corner of the status area and press Enter...",
        "calibration_done": "Calibration finished.",
        "ocr_sample": "OCR result:",
        "focus_fail": "Could not find window — focusing by clicking INPUT_CLICK:",
        "checking": "Checking",
        "used": "Taken ❌",
        "free": "Available ✅",
        "free_already": "Available ✅ (already in file)",
        "free_saved": "Available ✅ (saving)",
        "unknown": "Unknown",
        "interrupted": "Interrupted by user (Ctrl+C).",
        "done": "Work finished.",
        "ocr_checking": "checking",
        "ocr_used": "already in use",
        "ocr_free": "available",
    }
}

CURRENT_LANG = "en"

def tr(key: str) -> str:
    return LANGS.get(CURRENT_LANG, LANGS["en"]).get(key, key)

# ---------- Конфиг по умолчанию ----------
DEFAULT_CONFIG = {
    "tesseract_cmd": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    "window_class": "",
    "window_title_part": "Pear Runtime",
    "input_click": [89, 231],
    "ocr_box": [106, 275, 400, 40],   # left, top, width, height
    "type_interval": 0.03,
    "delay_after_input": 0.4,
    "wait_result_timeout": 10.0,
    "wait_poll_interval": 0.35,
    "debug_screenshots": False,
    "debug_folder": "ocr_debug",
    "resume_state_file": "state.json",
    "out_file": "free_nicks.txt",
    "checked_file": "checked_nicks.txt",
    "used_file": "used_nicks.txt"
}

CONFIG_PATH = Path("config.json")

# ------------------ Утилиты ------------------
def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg

# ------------------ Калибратор ------------------
def calibrate_interactive(cfg: dict):
    print("\n" + tr("calibrator_title") + "\n")
    print(tr("calibrator_step1"))
    input(tr("calibrator_step2"))
    pos_input = pyautogui.position()
    print("INPUT_CLICK =", pos_input)

    input(tr("calibrator_step3"))
    tl = pyautogui.position()
    input(tr("calibrator_step4"))
    br = pyautogui.position()

    left = int(tl.x)
    top = int(tl.y)
    width = int(br.x - tl.x)
    height = int(br.y - tl.y)
    if width <= 0 or height <= 0:
        print(tr("unknown"))
        return

    cfg["input_click"] = [pos_input.x, pos_input.y]
    cfg["ocr_box"] = [left, top, width, height]
    save_config(cfg)
    print("\nconfig.json saved")

    # пробный скрин и OCR
    Path(cfg.get("debug_folder", "ocr_debug")).mkdir(exist_ok=True)
    sample = pyautogui.screenshot(region=(left, top, width, height))
    sample_path = Path(cfg["debug_folder"]) / "ocr_sample.png"
    sample.save(sample_path)
    print(f"Screenshot saved: {sample_path}")

    pytesseract.pytesseract.tesseract_cmd = cfg.get("tesseract_cmd") or pytesseract.pytesseract.tesseract_cmd
    try:
        txt = pytesseract.image_to_string(sample, lang="eng").strip()
    except Exception as e:
        txt = f"(OCR error: {e})"
    print(tr("ocr_sample"), repr(txt))
    print("\n" + tr("calibration_done"))

# ------------------ tesseract с предобработкой ------------------
def ocr_preprocess_and_read(region: Tuple[int, int, int, int], cfg: dict) -> str:
    left, top, w, h = region
    img = pyautogui.screenshot(region=(left, top, w, h))
    img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    img_np = cv2.resize(img_np, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    _, th = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = cv2.medianBlur(th, 3)
    pil_img = Image.fromarray(th)
    pytesseract.pytesseract.tesseract_cmd = cfg.get("tesseract_cmd") or pytesseract.pytesseract.tesseract_cmd
    try:
        text = pytesseract.image_to_string(pil_img, lang="eng").strip().lower()
    except Exception:
        text = ""
    return text

# ------------------ Фокус окна ------------------
def focus_app_window(cfg: dict) -> bool:
    try:
        if cfg.get("window_class"):
            matches = findwindows.find_windows(class_name=cfg["window_class"], top_level_only=True)
            if matches:
                hwnd = matches[0]
                app = Application(backend="uia").connect(handle=hwnd)
                win = app.window(handle=hwnd)
                win.set_focus()
                time.sleep(0.2)
                return True
        if cfg.get("window_title_part"):
            matches = findwindows.find_windows(title_re=f".*{cfg['window_title_part']}.*", top_level_only=True)
            if matches:
                hwnd = matches[0]
                app = Application(backend="uia").connect(handle=hwnd)
                win = app.window(handle=hwnd)
                win.set_focus()
                time.sleep(0.2)
                return True
    except Exception:
        pass
    
    x, y = cfg["input_click"]
    print(tr("focus_fail"), (x, y))
    pyautogui.click(x, y)
    time.sleep(0.3)
    return True


# ------------------ Генератор ников ------------------
def generate_nicks(min_len=3, max_len=4, require_digit=True):
    letters = string.ascii_lowercase
    digits = string.digits
    chars = letters + digits + "_"
    for length in range(min_len, max_len + 1):
        for combo in itertools.product(chars, repeat=length):
            nick = "".join(combo)
            if not any(c.isalpha() for c in nick):
                continue
            if require_digit and not any(c.isdigit() for c in nick):
                continue
            yield nick


# ------------------ статус результата ------------------
def wait_for_result(cfg: dict, timeout: float = None) -> Tuple[str, str]:
    timeout = timeout or cfg.get("wait_result_timeout", 10.0)
    poll = cfg.get("wait_poll_interval", 0.35)
    region = tuple(cfg["ocr_box"])
    start = time.time()
    last_text = ""
    while time.time() - start < timeout:
        text = ocr_preprocess_and_read(region, cfg)
        if text != last_text:
            print("OCR:", repr(text))
            last_text = text
        if tr("ocr_checking") in text:
            time.sleep(poll)
            continue
        if tr("ocr_used") in text:
            return "used", text
        if tr("ocr_free") in text:
            return "free", text
        time.sleep(poll)
    return "unknown", last_text

# ------------------ проверка ника ------------------
def try_nick(nick: str, cfg: dict) -> Tuple[str, str]:
    x, y = cfg["input_click"]
    pyautogui.click(x, y)
    time.sleep(0.05)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.02)
    pyautogui.press("backspace")
    time.sleep(0.02)
    pyautogui.typewrite(nick, interval=cfg.get("type_interval", 0.03))
    time.sleep(cfg.get("delay_after_input", 0.4))
    pyautogui.press("enter")
    return wait_for_result(cfg)


# ------------------ Цикл перебора ------------------
def run_loop(cfg: dict, min_len: int = 2, max_len: int = 3, require_digit: bool = True,
             resume: bool = True, max_checks: int = None):
    print("Config loaded...")
    if cfg.get("tesseract_cmd"):
        pytesseract.pytesseract.tesseract_cmd = cfg["tesseract_cmd"]

    out_path = Path(cfg.get("out_file", "free_nicks.txt"))
    checked_path = Path(cfg.get("checked_file", "checked_nicks.txt"))
    used_path = Path(cfg.get("used_file", "used_nicks.txt"))

    out_path.touch(exist_ok=True)
    checked_path.touch(exist_ok=True)
    used_path.touch(exist_ok=True)
    
    # проверенные и свободные
    with checked_path.open("r", encoding="utf-8") as f:
        checked = set(line.strip() for line in f if line.strip())
    with out_path.open("r", encoding="utf-8") as f:
        free_existing = set(line.strip() for line in f if line.strip())

    print(f"{len(checked)} checked. {len(free_existing)} free already in file.")


    focus_app_window(cfg)

    checked_count = 0
    try:
        for nick in generate_nicks(min_len, max_len, require_digit):
            if max_checks and checked_count >= max_checks:
                break
            if nick in checked:
                continue
            print(tr("checking") + f": {nick} ...", end=" ", flush=True)
            status, txt = try_nick(nick, cfg)
            if status == "used":
                print(tr("used"))
                with used_path.open("a", encoding="utf-8") as f:
                    f.write(nick + "\n")
            elif status == "free":
                if nick in free_existing:
                    print(tr("free_already"))
                else:
                    print(tr("free_saved"))
                    with out_path.open("a", encoding="utf-8") as f:
                        f.write(nick + "\n")
                    free_existing.add(nick)
            else:
                print(tr("unknown"), f"(OCR='{txt}')")
            with checked_path.open("a", encoding="utf-8") as f:
                f.write(nick + "\n")
            checked.add(nick)
            checked_count += 1
            time.sleep(0.12)
    except KeyboardInterrupt:
        print(tr("interrupted"))
    finally:
        dedupe_file(out_path)
        print(tr("done"))

def dedupe_file(path: Path):
    if not path.exists():
        return
    seen = set()
    lines = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\n")
            if s and s not in seen:
                seen.add(s)
                lines.append(s)
    with path.open("w", encoding="utf-8") as f:
        for ln in lines:
            f.write(ln + "\n")

# ------------------ CLI ------------------
def main():
    global CURRENT_LANG
    parser = argparse.ArgumentParser(description="Keet username checker")
    parser.add_argument("mode", choices=["calibrate", "run"], help="calibrate or run")
    parser.add_argument("--min-len", type=int, default=2, help="minimum nickname length (default 2)")
    parser.add_argument("--max-len", type=int, default=3, help="maximum nickname length (default 3)")
    parser.add_argument("--no-require-digit", action="store_true", help="allow nicks without digits")
    parser.add_argument("--no-resume", action="store_true", help="ignore checked_nicks.txt and recheck all")
    parser.add_argument("--max", type=int, default=0, help="max number of checks per run (0 = unlimited)")
    parser.add_argument("--lang", choices=["ru", "en"], default="en", help="language (default en)")
    args = parser.parse_args()
    CURRENT_LANG = args.lang

    cfg = load_config()
    if args.mode == "calibrate":
        calibrate_interactive(cfg)
    elif args.mode == "run":
        if args.no_resume:
            p = Path(cfg.get("checked_file", "checked_nicks.txt"))
            if p.exists():
                p.unlink()
        run_loop(cfg,
                 min_len=max(3, args.min_len),
                 max_len=max(3, args.max_len),
                 require_digit=(not args.no_require_digit),
                 resume=not args.no_resume,
                 max_checks=(args.max if args.max > 0 else None))

if __name__ == "__main__":
    main()

