"""
Daily English Words
Her gun 20 yeni Ingilizce kelime, Turkce cevirisi, ornek cumle
ve ornek cumlenin Turkce cevirisi ile mail gonderir.

Veri kaynaklari:
- words_10k.txt: ~8750 sik kullanilan Ingilizce kelimeden olusan havuz
  (google-10000-english listesinden stopword/kisa kelime filtrelenerek turetildi)
- Wiktionary REST API (ucretsiz, API key gerektirmez): tanim + ornek cumle
- Wiktionary "Turkish translations" tablosu: kelimenin doğru Turkce karsiligi
  (birincil kaynak; MyMemoryTranslator sadece yedek olarak kullanilir)
- Supheli/bozuk ceviri gelirse o kelime atlanip baska kelime secilir

Tekrar onleme:
- used_words.json dosyasinda simdiye kadar gonderilen tum kelimeler tutulur.
- Her calismada bu dosyadan hic kullanilmamis kelimeler secilir.
- Workflow, mail basariyla gonderildikten sonra bu dosyayi repoya geri commitler.
"""

import json
import os
import random
import re
import smtplib
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from deep_translator import MyMemoryTranslator

WORDS_PER_DAY = 20
WORDS_FILE = os.path.join(os.path.dirname(__file__), "words_10k.txt")
USED_WORDS_FILE = os.path.join(os.path.dirname(__file__), "used_words.json")

WIKTIONARY_HEADERS = {
    "User-Agent": "DailyEnglishWordsBot/1.0 (https://github.com/Mehmetusakk/sabah-brifingi)"
}


def load_word_pool():
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_used_words():
    if not os.path.exists(USED_WORDS_FILE):
        return set()
    with open(USED_WORDS_FILE, "r", encoding="utf-8") as f:
        try:
            return set(json.load(f))
        except Exception:
            return set()


def save_used_words(used_words):
    with open(USED_WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(used_words), f, ensure_ascii=False, indent=2)


def _clean_html(raw_html):
    text = re.sub("<[^<]+?>", "", raw_html or "").strip()
    text = " ".join(text.split())
    return text


def fetch_word_info(word, retries=2):
    url = f"https://en.wiktionary.org/api/rest_v1/page/definition/{word}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=10, headers=WIKTIONARY_HEADERS)
            if resp.status_code != 200:
                return None
            data = resp.json()
            entries = data.get("en") or []
            for entry in entries:
                part_of_speech = entry.get("partOfSpeech", "")
                for definition in entry.get("definitions", []):
                    def_text = _clean_html(definition.get("definition", ""))
                    examples = definition.get("examples") or []
                    if not def_text or not examples:
                        continue
                    example_text = _clean_html(examples[0])
                    if len(def_text) < 3 or len(example_text) < 3:
                        continue
                    return {
                        "word": word,
                        "part_of_speech": part_of_speech,
                        "definition": def_text,
                        "example": example_text,
                    }
            return None
        except Exception as exc:
            print(f"UYARI: {word} icin Wiktionary sorgusu basarisiz ({exc}), deneme {attempt + 1}", file=sys.stderr)
            time.sleep(1)
    return None


def _safe_translate(text, retries=3):
    if not text:
        return text
    for attempt in range(retries):
        try:
            return MyMemoryTranslator(source="en-US", target="tr-TR").translate(text[:490])
        except Exception as exc:
            print(f"UYARI: ceviri basarisiz ({exc}), deneme {attempt + 1}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return text


def _is_bad_translation(word, translation):
    if not translation:
        return True
    w = word.strip().lower()
    t = translation.strip().lower()
    if t == w:
        return True
    if t.endswith(w) and len(t) - len(w) <= 2:
        return True
    if len(t) < 2:
        return True
    letters = re.sub(r"[^a-zA-ZçğıöşüÇĞİÖŞÜ]", "", t)
    if len(letters) < 2:
        return True
    if "," in t or len(t.split()) > 3:
        return True
    english_suffixes = ("tion", "sion", "ment", "ness", "able", "ible", "ing", "ed", "ly")
    if len(t.split()) == 1 and t.endswith(english_suffixes):
        return True
    return False


def fetch_wiktionary_word_translation(word, retries=2):
    url = f"https://en.wiktionary.org/w/index.php?title={word}&action=raw"
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=10, headers=WIKTIONARY_HEADERS)
            if resp.status_code != 200:
                return None
            match = re.search(r"\* ?Turkish: (.+)", resp.text)
            if not match:
                return None
            candidates = re.findall(r"\{\{t\+?\|tr\|([^|}]+)", match.group(1))
            if not candidates:
                return None
            return candidates[0].strip()
        except Exception as exc:
            print(f"UYARI: {word} icin Wiktionary ceviri sorgusu basarisiz ({exc}), deneme {attempt + 1}", file=sys.stderr)
            time.sleep(1)
    return None


def translate_word(word):
    translation = fetch_wiktionary_word_translation(word)
    if translation and not _is_bad_translation(word, translation):
        return translation

    translation = _safe_translate(word)
    if translation and not _is_bad_translation(word, translation):
        return translation

    return None


def pick_daily_words(pool, used_words, count=WORDS_PER_DAY):
    available = [w for w in pool if w not in used_words]
    if len(available) < count:
        print("UYARI: kullanilmamis kelime havuzu azaldi, used_words.json sifirlaniyor", file=sys.stderr)
        used_words.clear()
        available = list(pool)

    random.shuffle(available)
    chosen = []
    for word in available:
        if len(chosen) >= count:
            break
        info = fetch_word_info(word)
        if not info:
            continue
        translation = translate_word(word)
        if not translation:
            continue
        info["translation"] = translation
        time.sleep(0.8)
        info["definition_tr"] = _safe_translate(info["definition"])
        time.sleep(0.8)
        info["example_tr"] = _safe_translate(info["example"])
        time.sleep(0.8)
        chosen.append(info)
    return chosen


def build_email_html(words):
    cards = ""
    for w in words:
        pos = f" <span style='color:#999; font-size:12px;'>({w['part_of_speech']})</span>" if w["part_of_speech"] else ""
        cards += f"""
        <div style="background:#f9f9f9; border-left:4px solid #1a73e8; padding:12px 14px; margin-bottom:14px; border-radius:4px;">
          <div style="font-weight:700; font-size:16px; color:#222;">{w['word'].capitalize()}{pos} &rarr; {w['translation']}</div>
          <div style="color:#444; font-size:13px; margin-top:6px;"><b>Anlami:</b> {w['definition']}</div>
          <div style="color:#666; font-size:13px; margin-top:4px;"><b>Anlami (TR):</b> {w['definition_tr']}</div>
          <div style="color:#333; font-size:13px; margin-top:8px;"><b>Ornek:</b> {w['example']}</div>
          <div style="color:#1a73e8; font-size:13px; margin-top:2px;"><b>Ornek (TR):</b> {w['example_tr']}</div>
        </div>"""

    html = f"""
    <html>
    <body style="font-family: -apple-system, Helvetica, Arial, sans-serif; max-width:640px; margin:0 auto; padding:20px; color:#222;">
      <h1 style="font-size:22px;">Gunun Ingilizce Kelimeleri</h1>
      <p style="color:#555;">Bugun icin secilen {len(words)} yeni kelime, Turkce karsiligi, anlami ve ornek cumlesiyle asagida.</p>
      {cards}
      <p style="color:#aaa; font-size:12px; margin-top:32px;">Bu mail her sabah otomatik olarak gonderilir. Kaynak: Wiktionary. Gonderilen kelimeler bir daha tekrar edilmez.</p>
    </body>
    </html>
    """
    return html


def send_email(html_body, subject):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    mail_to_list = os.environ.get("MAIL_TO_LIST", os.environ.get("MAIL_TO", gmail_user))

    recipients = [addr.strip() for addr in mail_to_list.split(",") if addr.strip()]
    if not recipients:
        print("HATA: MAIL_TO_LIST bos veya tanimli degil, mail gonderilemedi", file=sys.stderr)
        sys.exit(1)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_app_password)
        for recipient in recipients:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = gmail_user
            msg["To"] = recipient
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            server.sendmail(gmail_user, [recipient], msg.as_string())

    print(f"Mail {len(recipients)} kisiye gonderildi: {', '.join(recipients)}")


def main():
    pool = load_word_pool()
    used_words = load_used_words()

    words = pick_daily_words(pool, used_words)
    if not words:
        print("HATA: hic kelime secilemedi, cikiliyor", file=sys.stderr)
        sys.exit(1)

    html = build_email_html(words)
    send_email(html, "Gunun Ingilizce Kelimeleri")

    used_words.update(w["word"] for w in words)
    save_used_words(used_words)
    print(f"{len(words)} yeni kelime used_words.json dosyasina eklendi.")


if __name__ == "__main__":
    main()
