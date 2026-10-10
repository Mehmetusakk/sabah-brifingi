#!/usr/bin/env python3
"""
Her sabah 09:00'da calisan, bir onceki gun 09:00'dan bu yana cikan onemli
gelismeleri 6 kategoride toplayip Turkce'ye cevirerek ozetleyen ve tek basina
+ sadece AI kullanarak kurulabilecek girisim fikirleri oneren mail scripti.

Gerekli ortam degiskenleri:
  GMAIL_USER          -> gonderen gmail adresi
  GMAIL_APP_PASSWORD  -> gmail "uygulama sifresi"
  MAIL_TO             -> alici adres
"""

import os
import random
import smtplib
import sys
import time
from calendar import timegm
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import feedparser
import requests
from deep_translator import MyMemoryTranslator

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SabahBrifingiBot/1.0)"}
ITEMS_PER_CATEGORY = 4
WINDOW_HOURS = 24  # bir onceki 09:00'dan bu 09:00'a kadar

FEEDS = {
    "Teknoloji": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ],
    "Dunya ve Jeopolitik": [
        ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "Turkiyede Is Firsatlari": [
        ("Webrazzi", "https://webrazzi.com/feed/"),
        ("AA Ekonomi", "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"),
    ],
    "Turkiye Guncel Ekonomik Haberleri": [
        ("BloombergHT", "https://www.bloomberght.com/rss"),
        ("Dunya Gazetesi", "https://www.dunya.com/rss?kategori=ekonomi"),
    ],
    "Yapay Zeka": [
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ],
    "Gunun Firsat Yazilim Projeleri": [
        ("Hacker News - Show HN", "https://hnrss.org/show"),
    ],
}

CATEGORY_TITLES_TR = {
    "Teknoloji": "Teknoloji",
    "Dunya ve Jeopolitik": "Dunya ve Jeopolitik",
    "Turkiyede Is Firsatlari": "Turkiye'de Is Firsatlari",
    "Turkiye Guncel Ekonomik Haberleri": "Turkiye Guncel Ekonomik Haberleri",
    "Yapay Zeka": "Yapay Zeka",
    "Gunun Firsat Yazilim Projeleri": "Gunun Firsat Yazilim Projeleri",
}

ALREADY_TURKISH = {"Turkiyede Is Firsatlari", "Turkiye Guncel Ekonomik Haberleri"}

ACTION_TIPS = {
    "Teknoloji": [
        "Bu teknolojiyi/urunu App Store veya Google Play'de ara; Turkiye'de benzer bir cozum var mi kontrol et.",
        "Haberdeki sirketin is modelini incele; AI ile tek basina uyarlayabilecegin kucuk bir versiyonu var mi?",
    ],
    "Dunya ve Jeopolitik": [
        "Bu gelismenin doviz kuru veya emtia fiyatlarina etkisini kontrol et; yan projelerinde bir risk/firsat var mi dusun.",
        "Bu gelisme Turkiye'deki hangi sektorleri (lojistik, enerji, turizm, e-ticaret) etkiler bir dakika dusun.",
    ],
    "Turkiyede Is Firsatlari": [
        "Haberdeki firma/sektorle baglantili birine LinkedIn'den mesaj at; ag kurmaya 5 dakika ayir.",
        "Bu firsati/trendi not al; 3-6 aylik girisim planinla kesisen bir yani var mi degerlendir.",
    ],
    "Turkiye Guncel Ekonomik Haberleri": [
        "Bu veri/kararin yan projelerine (fiyatlama, maliyet, yatirim zamanlamasi) etkisini bir dakika dusun.",
    ],
    "Yapay Zeka": [
        "Bu AI aracini/modelini dene; tek basina kurabilecegin bir urun veya otomasyona donusturulebilir mi?",
    ],
    "Gunun Firsat Yazilim Projeleri": [
        "Bu projeyi incele; ayni fikri Turkiye pazarina veya farkli bir niseye AI ile tek basina uyarlayabilir misin?",
    ],
}

INTRO_LINES = [
    "Gunaydin Mehmet, dunya gece de durmadi, iste bilmen gerekenler.",
    "Gunaydin! Bugun seni bekleyen gelismeler ve girisim firsatlari asagida.",
    "Yeni bir gun, yeni gelismeler. Iste son 24 saatin ozeti.",
]

# -----------------------------------------------------------------------
# Girisim fikri sablonlari: anahtar kelime -> (ihtiyac, AI ile tek basina
# yapilabilecek urun fikri, ilk adim)
# -----------------------------------------------------------------------
IDEA_TEMPLATES = [
    (["ai", "yapay zeka", "artificial intelligence", "model", "chatgpt", "openai", "agent"],
     "AI Destekli Niche Otomasyon Araci",
     "Haberdeki AI modelini/araci bir API olarak kullanip, kucuk isletmeler icin "
     "tek bir sikayeti cozen basit bir SaaS arayuzu kur (ör. fatura ozetleme, "
     "musteri mesaji yanitlama, icerik uretme). Kodun cogunu AI ile yaz, "
     "no-code arayuz (ör. Lovable/Bubble) ile birlestir.",
     "Bugun o API'nin ucretsiz kotasiyla 1 saatlik bir prototip dene."),
    (["startup", "girisim", "yatirim", "funding", "finansman"],
     "Mikro-SaaS: Bu Girisimin Kucuk Versiyonu",
     "Haberdeki girisimin cozdugu problemin kucuk, tek kullanicili / tek "
     "ekip icin yeterli bir 'mini' versiyonunu AI ile kodlayip aylik "
     "abonelikle sat.",
     "Haberdeki sirketin web sitesine gir, fiyatlandirma sayfasini incele."),
    (["e-ticaret", "ecommerce", "perakende", "retail"],
     "AI Destekli E-ticaret Yan Araci",
     "Kucuk e-ticaret satici icin urun aciklamasi/gorsel/SEO ureten bir "
     "AI araci yap; Shopify/Trendyol/Ikas entegrasyonu ile tek basina "
     "satabilecegin bir eklenti haline getir.",
     "Bir pazar yerinde 10 kucuk satici bul, DM ile ihtiyaclarini sor."),
    (["enerji", "energy", "iklim", "climate", "cevre", "surdurulebilir"],
     "Surdurulebilirlik Raporlama Araci",
     "KOBI'lerin karbon ayak izini / enerji tuketimini AI ile otomatik "
     "hesaplayip rapor ureten basit bir web araci kur (AB uyum "
     "zorunluluklari arttikca talep artiyor).",
     "3 KOBI'ye bu raporu şu an nasil hazirladiklarini sor."),
    (["is gucu", "istihdam", "issizlik", "employment", "isci"],
     "AI ile Ise Alim/Egitim Araci",
     "Kucuk sirketler icin AI destekli mulakat on elemesi veya yeni "
     "calisan onboarding/egitim materyali ureten bir arac gelistir.",
     "LinkedIn'de 5 IK uzmanina bu surecte en cok vakit kaybettikleri "
     "yeri sor."),
    (["finans", "bankacilik", "banking", "faiz", "kur", "enflasyon"],
     "Kisisel Finans AI Asistani (Niche)",
     "Belirli bir hedef kitleye (freelancer, esnaf, yan is yapanlar) "
     "ozel, AI ile gelir-gider/vergi tahmini yapan basit bir arac kur.",
     "Kendi gelir-gider verinle bir prototip dene, isteyene demo goster."),
    (["saglik", "health", "healthcare", "ilaç"],
     "AI Destekli Saglik Takip/Hatirlatma Araci",
     "Kronik hastalik takibi veya ilac hatirlatma gibi dar bir alanda, "
     "AI ile kisisellestirilmis basit bir mobil/web araci gelistir.",
     "Bir hasta/yakin grubu forumunda en cok sikayet edilen noktayi bul."),
    (["egitim", "education", "ogrenci", "universite"],
     "AI Destekli Mikro-Egitim Platformu",
     "Dar bir konuda (ör. bir sinav, bir yazilim dili) AI ile kisisellestirilmis "
     "mikro-ders/quiz ureten bir platform kur; tek basina icerik + kod "
     "uretimini AI'a yaptir.",
     "Bir Telegram/Discord ogrenci grubuna gir, en cok sorulan soruyu not et."),
]

GENERIC_IDEAS = [
    ("AI Icerik Ajansi (Tek Kisilik)",
     "Kucuk isletmelere sosyal medya/blog icerigini tamamen AI araclariyla "
     "uretip yoneten, aylik abonelikle calisan bir hizmet kur.",
     "3 esnaf/KOBI'ye sosyal medya yonetimini kime yaptirdiklarini sor."),
    ("Dar Niche AI SaaS",
     "Gunluk takip ettigin bir sektorde (ör. emlak, lojistik, hukuk) "
     "tek bir sikayeti cozen, tamamen AI ile kodlanmis basit bir SaaS urunu "
     "gelistirip Product Hunt'ta lansla.",
     "Bugun Reddit/Twitter'da o sektorle ilgili 5 sikayet ara."),
]


def _to_utc_struct_cutoff(hours):
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _entry_datetime(entry):
    for field in ("published_parsed", "updated_parsed"):
        value = getattr(entry, field, None)
        if value:
            return datetime.fromtimestamp(timegm(value), tz=timezone.utc)
    return None


def fetch_category_items(sources, limit=ITEMS_PER_CATEGORY, window_hours=WINDOW_HOURS):
    cutoff = _to_utc_struct_cutoff(window_hours)
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
            entry_dt = _entry_datetime(entry)
            if entry_dt is not None and entry_dt < cutoff:
                continue
            seen_titles.add(title)
            link = getattr(entry, "link", "")
            summary = _clean_summary(getattr(entry, "summary", "") or getattr(entry, "description", ""))
            items.append({"title": title, "link": link, "summary": summary, "source": source_name})
        if len(items) >= limit:
            break
    if not items:
        # Zaman penceresinde hic haber yoksa, bos birakmak yerine en guncel
        # birkac basligi (tarihe bakmadan) goster.
        return fetch_category_items(sources, limit=limit, window_hours=24 * 7)
    return items[:limit]


def _clean_summary(raw_html, max_len=200):
    import re

    text = re.sub("<[^<]+?>", "", raw_html or "").strip()
    text = " ".join(text.split())
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "..."
    return text


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


def translate_items(items):
    for item in items:
        item["title"] = _safe_translate(item["title"])
        time.sleep(0.5)
        item["summary"] = _safe_translate(item["summary"])
        time.sleep(0.5)
    return items


def generate_startup_ideas(all_items, rng, count=3):
    text_blob = " ".join((it["title"] + " " + it["summary"]).lower() for it in all_items)
    matched = []
    for keywords, name, desc, first_step in IDEA_TEMPLATES:
        if any(kw in text_blob for kw in keywords):
            source_item = next(
                (it for it in all_items if any(kw in (it["title"] + it["summary"]).lower() for kw in keywords)),
                None,
            )
            matched.append((name, desc, first_step, source_item))

    rng.shuffle(matched)
    ideas = matched[:count]
    if len(ideas) < count:
        remaining = [(n, d, s, None) for n, d, s in GENERIC_IDEAS]
        rng.shuffle(remaining)
        ideas += remaining[: count - len(ideas)]
    return ideas[:count]


def build_email_html(categories_data, all_items, day_seed):
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
        title_tr = CATEGORY_TITLES_TR.get(category, category)

        sections_html.append(f"""
        <h2 style="font-size:18px; color:#222; border-bottom:2px solid #eee; padding-bottom:6px; margin-top:28px;">{title_tr}</h2>
        <ul style="list-style:none; padding-left:0;">{headline_html}</ul>
        {"<div style='background:#f0f6ff; border-left:4px solid #1a73e8; padding:10px 14px; font-size:13px; color:#333;'><b>Bugun ne yapabilirsin:</b> " + tip + "</div>" if tip else ""}
        """)

    ideas = generate_startup_ideas(all_items, rng)
    ideas_html = ""
    for name, desc, first_step, source_item in ideas:
        kaynak_html = ""
        if source_item:
            kaynak_html = f"<div style='color:#999; font-size:12px; margin-top:4px;'>Ilham kaynagi: <a href='{source_item['link']}' style='color:#999;'>{source_item['title']}</a></div>"
        ideas_html += f"""
        <div style="background:#fff8e6; border-left:4px solid #f5a623; padding:12px 14px; margin-bottom:14px; border-radius:4px;">
          <div style="font-weight:700; font-size:15px; color:#222;">{name}</div>
          <div style="color:#444; font-size:13px; margin-top:4px;">{desc}</div>
          <div style="color:#b35c00; font-size:13px; margin-top:6px;"><b>Ilk adim:</b> {first_step}</div>
          {kaynak_html}
        </div>"""

    ideas_section = f"""
    <h2 style="font-size:18px; color:#222; border-bottom:2px solid #eee; padding-bottom:6px; margin-top:32px;">Girisim Firsatlari (Tek Basina + Sadece AI ile)</h2>
    <p style="color:#555; font-size:13px;">Bugunun haberlerinden yola cikarak, 3-6 ay icinde tek basina ve AI araclariyla hayata gecirebilecegin fikirler:</p>
    {ideas_html}
    """

    html = f"""
    <html>
    <body style="font-family: -apple-system, Helvetica, Arial, sans-serif; max-width:640px; margin:0 auto; padding:20px; color:#222;">
      <h1 style="font-size:22px;">Sabah Brifingi</h1>
      <p style="color:#555;">{intro}</p>
      {"".join(sections_html)}
      {ideas_section}
      <p style="color:#aaa; font-size:12px; margin-top:32px;">Bu mail her sabah otomatik olarak gonderilir. Kaynaklar: BBC, Al Jazeera, TechCrunch, The Verge, Webrazzi, AA, BloombergHT, Dunya Gazetesi, Hacker News.</p>
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
    all_items = []
    for category, sources in FEEDS.items():
        items = fetch_category_items(sources)
        if category not in ALREADY_TURKISH:
            items = translate_items(items)
        categories_data[category] = items
        all_items.extend(items)

    html = build_email_html(categories_data, all_items, day_seed=now.strftime("%Y%m%d"))
    subject = f"Sabah Brifingi - {now.strftime('%d %B %Y')}"
    send_email(html, subject)
    print("Mail gonderildi:", subject)


if __name__ == "__main__":
    main()
