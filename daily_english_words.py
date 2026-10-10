"""
Daily English Words
Her gun 20 yeni Ingilizce kelime (4 grup x 5), Turkce cevirisi, ornek cumle
ve ornek cumlenin Turkce cevirisi ile mail gonderir.

Veri kaynaklari:
- words_10k.txt: ~8750 sik kullanilan Ingilizce kelimeden olusan havuz
  (google-10000-english listesinden stopword/kisa kelime filtrelenerek turetildi)
- Wiktionary REST API (ucretsiz, API key gerektirmez): tanim + ornek cumle
- deep-translator / MyMemoryTranslator (ucretsiz): Turkce ceviri

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
GROUP_SIZE = 5
WORDS_FILE = os.path.join(os.path.dirname(__file__), "words_10k.txt")
USED_WORDS_FILE = os.path.join(os.path.dirname(__file__), "used_words.json")

GROUP_NAMES_TR = ["1. Grup", "2. Grup", "3. Grup", "4. Grup"]

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


def _safe_translate(text, retries=2):
    if not text:
        return text
    for attempt in range(retries):
        try:
            return MyMemoryTranslator(source="en-US", target="tr-TR").translate(text[:490])
        except Exception as exc:
            print(f"UYARI: ceviri basarisiz ({exc}), deneme {attempt + 1}", file=sys.stderr)
            time.sleep(1.5)
    return text


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
        info["translation"] = _safe_translate(info["word"])
        time.sleep(0.4)
        info["definition_tr"] = _safe_translate(info["definition"])
        time.sleep(0.4)
        info["example_tr"] = _safe_translate(info["example"])
        time.sleep(0.4)
        chosen.append(info)
    return chosen


def build_email_html(words):
    groups = [words[i:i + GROUP_SIZE] for i in range(0, len(words), GROUP_SIZE)]

    sections_html = []
    for idx, group in enumerate(groups):
        group_name = GROUP_NAMES_TR[idx] if idx < len(GROUP_NAMES_TR) else f"{idx + 1}. Grup"
        cards = ""
        for w in group:
            pos = f" <span style='color:#999; font-size:12px;'>({w['part_of_speech']})</span>" if w["part_of_speech"] else ""
            cards += f"""
            <div style="background:#f9f9f9; border-left:4px solid #1a73e8; padding:12px 14px; margin-bottom:14px; border-radius:4px;">
              <div style="font-weight:700; font-size:16px; color:#222;">{w['word'].capitalize()}{pos} &rarr; {w['translation']}</div>
              <div style="color:#444; font-size:13px; margin-top:6px;"><b>Anlami:</b> {w['definition']}</div>
              <div style="color:#666; font-size:13px; margin-top:4px;"><b>Anlami (TR):</b> {w['definition_tr']}</div>
              <div style="color:#333; font-size:13px; margin-top:8px;"><b>Ornek:</b> {w['example']}</div>
              <div style="color:#1a73e8; font-size:13px; margin-top:2px;"><b>Ornek (TR):</b> {w['example_tr']}</div>
            </div>"""

        sections_html.append(f"""
        <h2 style="font-size:18px; color:#222; border-bottom:2px solid #eee; padding-bottom:6px; margin-top:28px;">{group_name}</h2>
        {cards}
        """)

    html = f"""
    <html>
    <body style="font-family: -apple-system, Helvetica, Arial, sans-serif; max-width:640px; margin:0 auto; padding:20px; color:#222;">
      <h1 style="font-size:22px;">Gunun Ingilizce Kelimeleri</h1>
      <p style="color:#555;">Bugun icin secilen {len(words)} yeni kelime, Turkce karsiligi, anlami ve ornek cumlesiyle asagida.</p>
      {"".join(sections_html)}
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
