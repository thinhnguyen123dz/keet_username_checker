# Keet Username Checker

**Keet Username Checker** is a Python automation tool that generates, tests, and verifies available usernames in Keet using OCR (Tesseract + OpenCV) and GUI automation.

[🇷🇺 Читать на русском](./README_RU.md)

📹 Demo video: [Watch on YouTube](https://www.youtube.com/watch?v=xmpNrbXmt4k)

It automatically:
- Generates usernames with rules (letters + digits, min length 3).
- Avoids duplicates and re-checks.
- Saves checked, taken, and free usernames.
- Uses OCR to read Keet's availability messages.
- Supports multi-language interface (English + Russian).

## ⚡ Features
- Automated username checking in Keet.
- OCR-based detection (pytesseract + opencv).
- Works with Windows GUI via pyautogui and pywinauto.
- Resume from last run.
- Multi-language support (--lang en / --lang ru).

## 📦 Installation
Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/keet-username-checker.git
```
cd keet-username-checker

Install dependencies:
pip install -r requirements.txt

Install Tesseract OCR:
Download: https://github.com/tesseract-ocr/tesseract
After installation, add the Tesseract path to your system PATH.

## ▶️ Usage
Run:
python keet.py run --lang en

Options:
- --lang en/ru        Language selection
- --min_len N         Minimum username length (default 3)
- --max_len N         Maximum username length
- --no-resume         Do not resume from previous session
- --no-require-digit  Allow usernames without digits

## Output Files
- free_nicks.txt — available usernames ✅
- used_nicks.txt — taken usernames ❌
- checked_nicks.txt — all tested usernames 📝

## License
This project is licensed under the **MIT license**. See [`LICENSE`](./LICENSE) for more information.
