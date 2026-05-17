# Digest

An AI-powered PDF summariser for Linux. Open any PDF, click Generate Summary, and get a clean one-page summary with 5–10 key points — powered by your choice of AI model via OpenRouter.

---

## Features

- **One-click summaries** — open a PDF and generate a structured summary in seconds
- **5–10 key bullet points** — the most important facts, arguments, and findings
- **OCR support** — automatically detects scanned PDFs and offers to run OCR via Tesseract
- **Large PDF support** — automatically splits oversized documents into chunks and combines them
- **Save as PDF or TXT** — export your summary in either format
- **Copy to clipboard** — paste your summary anywhere instantly
- **Model choice** — use Claude, GPT-4, Gemini, or any model available on OpenRouter

---

## Requirements

- Ubuntu 24.04 / Linux Mint 22.x (or any GTK3-capable Linux)
- Python 3.10+
- An OpenRouter API key (free tier available at [openrouter.ai/keys](https://openrouter.ai/keys))

---

## Installation

### Option 1 — Installer script (recommended)

```bash
cd digest/
chmod +x install.sh
./install.sh
```

Then launch with:
```bash
digest
```

Or search for **Digest** in your application menu.

### Option 2 — Run directly without installing

Install dependencies:

```bash
sudo apt install \
  python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
  python3-requests \
  gir1.2-poppler-0.18 \
  tesseract-ocr python3-pil

pip3 install --user pypdf pytesseract
```

Then run:

```bash
cd digest/
python3 digest.py
```

---

## First-time setup

1. Launch Digest
2. Click **⚙ Settings** (top-right)
3. Enter your **OpenRouter API key**
4. Choose a model — Claude 3.5 Sonnet is recommended
5. Click **Save**

---

## Usage

1. Click **Open PDF** and select a file
2. If the PDF is a scanned image, a warning bar appears — click **Run OCR** to extract the text
3. Click **Generate Summary**
4. For large PDFs, Digest splits the document into chunks and shows progress (e.g. "Summarising part 2 of 4…")
5. Once complete, use **Copy**, **Save as TXT**, or **Save as PDF**

---

## OCR (scanned PDFs)

Digest automatically detects PDFs with little or no selectable text and offers to run OCR. Tesseract renders each page at high resolution and extracts the text before summarising.

OCR requires:
```bash
sudo apt install tesseract-ocr python3-pil
pip3 install --user pytesseract
```

For documents in languages other than English, install the relevant Tesseract language pack:
```bash
sudo apt install tesseract-ocr-deu   # German
sudo apt install tesseract-ocr-fra   # French
sudo apt install tesseract-ocr-spa   # Spanish
```

---

## Recommended models (via OpenRouter)

| Model | Notes |
|---|---|
| `anthropic/claude-3.5-sonnet` | Best overall quality (default) |
| `openai/gpt-4o` | Strong alternative |
| `openai/gpt-4o-mini` | Faster, lower cost |
| `google/gemini-pro-1.5` | Long context window |

---

## Disk space

| Component | Size |
|---|---|
| Digest app | < 100 KB |
| python3-gi, gir1.2-gtk-3.0 (usually pre-installed) | ~1.5 MB |
| tesseract-ocr | ~30 MB |
| reportlab (for PDF export, usually pre-installed) | ~5 MB |

---

## Data storage

| Data | Location |
|---|---|
| Settings & API key | `~/.config/digest/config.json` |

---

## Troubleshooting

**"No API key configured"**
Open Settings (⚙) and enter your OpenRouter API key from [openrouter.ai/keys](https://openrouter.ai/keys).

**PDF shows no text / OCR button not appearing**
```bash
sudo apt install tesseract-ocr python3-pil
pip3 install --user pytesseract
```

**App won't start**
```bash
python3 /opt/digest/digest.py
```
Run from terminal to see error messages.

---

## Uninstall

```bash
sudo rm -rf /opt/digest
sudo rm -f /usr/local/bin/digest
sudo rm -f /usr/share/applications/digest.desktop
sudo rm -f /usr/share/icons/hicolor/scalable/apps/digest.svg
rm -rf ~/.config/digest
```
