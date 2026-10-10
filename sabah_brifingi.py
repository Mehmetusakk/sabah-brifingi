#!/usr/bin/env python3
"""
Her sabah calisan, dunyadaki onemli gelismeleri (dunya/jeopolitik, teknoloji,
cevre, is & firsat) toplayip Turkce bir "sabah brifingi" maili gonderen script.

Gmail SMTP kullanir. Gerekli ortam degiskenleri:
  GMAIL_USER          -> gonderen gmail adresi
  GMAIL_APP_PASSWORD  -> gmail "uygulama sifresi"
  MAIL_TO             -> alici adres (varsayilan: GMAIL_USER ile ayni)
"""

import os
import random
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import feedparser
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SabahBrifingiBot/1.0)"}

FEEDS = {
    "Dunya & Jeopolitik": [
        ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "Teknoloji": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ],
    "Cevre": [
        ("The Guardian - Environment", "https://www.theguardian.com/environment/rss"),
    ],
    "Is & Firsat": [
        ("The Guardian - Business", "https://www.theguardian.com/business/rss"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
    ],
}

ITEMS_PER_CATEGORY = 3

ACTION_TIPS = {
    "Dunya & Jeopolitik": [
        "Bu gelismenin doviz kurlarina veya emtia fiyatlarina etkisini kontrol et; is planlarinda bir revizyon gerekiyor mu dusun.",
        "Haberi 2 cumleyle ozetleyip LinkedIn'de kendi yorumunla paylas; sektorundeki agin bunu nasil degerlendiriyor gor.",
        "Bu gelisme Turkiye'deki hangi sektorleri (lojistik, enerji, turizm, e-ticaret) etkiler diye bir dakika dusun.",
    ],
    "Teknoloji": [
        "Bu teknolojiyi/urunu App Store veya Google Play'de ara; Turkiye'de benzer bir cozum var mi kontrol et, yoksa bir fikir notu al.",
        "Haberdeki sirketin is modelini incele; kucuk olcekte (yan proje) uyarlayabilecegin bir parcasi var mi?",
        "Bu konuyla ilgili bir ChatGPT/Abacus ile 10 dakikalik 'bu trendden nasil para kazanilir' beyin firtinasi yap.",
    ],
    "Cevre": [
        "Bu haberle ilgili bir surdurulebilirlik/yesil girisim firsati var mi diye bak; yatirim veya is fikri notu al.",
        "Sirketinde veya yan projende bu konuyla ilgili kucuk bir aksiyon (enerji tasarrufu, surdurulebilir tedarikci vb.) planla.",
    ],
    "Is & Firsat": [
        "Haberdeki finansman/buyume modelini incele; benzer bir yan proje veya app fikrine uyarlanabilir mi degerlendir.",
        "Bu sektordeki bir firmaya LinkedIn'den bir profesyonel baglanti istegi gonder; ag kurmaya 5 dakika ayir.",
        "Nesine'deki rolunle kesisen bir noktasi var mi? Varsa bir not al, ekip ici bir fikir olarak sun.",
    ],
}

INTRO_LINES = [
    "Gunaydin Mehmet, dunya gece de durmadi, iste bilmen gerekenler.",
    "Gunaydin! Bugun seni bekleyen gelismeler ve olasi firsatlar asagida.",
    "Yeni bir gun, yeni gelismeler. Iste dunyadan ve firsatlardan ozet.",
]


def fetch_category_items(sources, limit=ITEMS_PER_CATEGORY):
    items = []
    seen_titles = set()
    for source_name, url in sources:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            print(f"UYARI: {source_name} okunamadi: {exc}", file=sys.stderr)
            continue
        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            link = getattr(entry, "link", "")
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary = _clean_summary(summary)
            items.append({"title": title, "link": link, "summary": summary, "source": source_name})
            if len(items) >= limit:
                break
        if len(items) >= limit:
            break
    return items[:limit]


def _clean_summary(raw_html, max_len=180):
    import re

    text = re.sub("<[^<]+?>", "", raw_html or "").strip()
    text = " ".join(text.split())
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "..."
    return text


def build_email_html(categories_data, day_seed):
    rng = random.Random(day_seed)
    intro = rng.choice(INTRO_LINES)

    sections_html = []
    for category, items in categories_data.items():
        if not items:
            continue
        headline_html = ""
        for item in items:
            headline_html += f"""
            <li style="margin-bottom:12px;">
              <a href="{item['link']}" style="color:#1a73e8; text-decoration:none; font-weight:600;">{item['title']}</a>
              <div style="color:#555; font-size:13px; margin-top:2px;">{item['summary']}</div>
              <div style="color:#999; font-size:12px; margin-top:2px;">Kaynak: {item['source']}</div>
            </li>"""

        tips = ACTION_TIPS.get(category, [])
        tip = rng.choice(tips) if tips else ""

        sections_html.append(f"""
        <h2 style="font-size:18px; color:#222; border-bottom:2px solid #eee; padding-bottom:6px; margin-top:28px;">{category}</h2>
        <ul style="list-style:none; padding-left:0;">{headline_html}</ul>
        {"<div style='background:#f0f6ff; border-left:4px solid #1a73e8; padding:10px 14px; font-size:13px; color:#333;'><b>Bugun ne yapabilirsin:</b> " + tip + "</div>" if tip else ""}
        """)

    html = f"""
    <html>
    <body style="font-family: -apple-system, Helvetica, Arial, sans-serif; max-width:640px; margin:0 auto; padding:20px; color:#222;">
      <h1 style="font-size:22px;">Sabah Brifingi</h1>
      <p style="color:#555;">{intro}</p>
      {"".join(sections_html)}
      <p style="color:#aaa; font-size:12px; margin-top:32px;">Bu mail her sabah otomatik olarak gonderilir. Kaynaklar: BBC, Al Jazeera, TechCrunch, The Verge, The Guardian.</p>
    </body>
    </html>
    """
    return html


def send_email(html_body, subject):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    mail_to = os.environ.get("MAIL_TO", gmail_user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = mail_to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_app_password)
        server.sendmail(gmail_user, [mail_to], msg.as_string())


def main():
    tz = ZoneInfo("Europe/Istanbul")
    now = datetime.now(tz)

    categories_data = {}
    for category, sources in FEEDS.items():
        categories_data[category] = fetch_category_items(sources)

    html = build_email_html(categories_data, day_seed=now.strftime("%Y%m%d"))
    subject = f"Sabah Brifingi - {now.strftime('%d %B %Y')}"
    send_email(html, subject)
    print("Mail gonderildi:", subject)


if __name__ == "__main__":
    main()
