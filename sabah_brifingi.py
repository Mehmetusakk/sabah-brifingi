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

# Siralama onemli: Turkiye'yi ilgilendiren kategoriler mailde her zaman
# en basta gosterilir.
FEEDS = {
    "Turkiyede Is Firsatlari": [
        ("Webrazzi", "https://webrazzi.com/feed/"),
        ("AA Ekonomi", "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"),
    ],
    "Turkiye Guncel Ekonomik Haberleri": [
        ("BloombergHT", "https://www.bloomberght.com/rss"),
        ("Dunya Gazetesi", "https://www.dunya.com/rss?kategori=ekonomi"),
    ],
    "Teknoloji": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ],
    "Yapay Zeka": [
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ],
    "Dunya ve Jeopolitik": [
        ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "Gunun Firsat Yazilim Projeleri": [
        ("Hacker News - Show HN", "https://hnrss.org/show"),
    ],
}

CATEGORY_TITLES_TR = {
    "Turkiyede Is Firsatlari": "Turkiye'de Is Firsatlari",
    "Turkiye Guncel Ekonomik Haberleri": "Turkiye Guncel Ekonomik Haberleri",
    "Teknoloji": "Teknoloji",
    "Yapay Zeka": "Yapay Zeka",
    "Dunya ve Jeopolitik": "Dunya ve Jeopolitik",
    "Gunun Firsat Yazilim Projeleri": "Gunun Firsat Yazilim Projeleri",
}

ALREADY_TURKISH = {"Turkiyede Is Firsatlari", "Turkiye Guncel Ekonomik Haberleri"}


# Kategori bazli, haber icerigine (anahtar kelimeye) gore secilen HAZIR analiz
# + oneri metinleri. Kullaniciya "git arastir" demek yerine, dogrudan ne
# anlama geldigini ve ne yapabilecegini soyler.
ANALYSIS_RULES = {
    "Teknoloji": [
        (["satin al", "acquisition", "acquire", "anlasma"],
         "Buyuk sirketlerin kucuk girisimleri satin almasi bu alanda hizli "
         "bir konsolidasyon oldugunu gosteriyor.",
         "Rakip olmaya calismak yerine, bu urunlerin API'siyle entegre "
         "calisan tamamlayici kucuk bir arac gelistirip o ekosisteme "
         "satmayi degerlendir."),
        (["yapay zeka", " ai ", "chatbot", "model"],
         "Ana akim teknoloji haberlerine bile AI ozellikleri tasiniyor; "
         "kullanicilarin AI araclarina aliskanligi hizla artiyor.",
         "Bu urunun Turkce ve yerel kullanim senaryosuna uyarlanmis kucuk "
         "bir versiyonunu AI ile tek basina hizlica prototipleyip test et."),
    ],
    "Yapay Zeka": [
        (["guvenlik", "safety", "regulasyon", "regulation", "frene"],
         "AI sirketleri guvenlik ve duzenleme baskisini daha fazla one "
         "cikariyor; bu, sektorun olgunlasma donemine girdigini gosteriyor.",
         "Kucuk isletmelere yonelik 'AI kullanim politikasi' veya 'guvenli "
         "AI entegrasyonu' danismanligi gibi dusuk maliyetli bir hizmeti "
         "tek basina sunabilirsin."),
    ],
    "Dunya ve Jeopolitik": [
        (["savas", "war", "israil", "gazze", "ukrayna", "rusya", "iran"],
         "Jeopolitik gerginlikler tedarik zinciri, enerji ve doviz "
         "tarafinda belirsizlik yaratmaya devam ediyor.",
         "Boyle donemlerde risk/fiyat takibi ihtiyaci artar; buna yonelik "
         "basit bir izleme araci (ornegin doviz/emtia alarm botu) fikrini "
         "degerlendirebilirsin."),
    ],
    "Turkiyede Is Firsatlari": [
        ([""],
         "Bu gelisme, Turkiye pazarinda kisa vadede hareketlenecek bir "
         "alani isaret ediyor.",
         "Haberdeki firma veya sektorle baglantili birine LinkedIn'den "
         "mesaj at; 3-6 aylik girisim planinla kesisen bir yani olup "
         "olmadigini bu hafta degerlendir."),
    ],
    "Turkiye Guncel Ekonomik Haberleri": [
        ([""],
         "Bu veri/karar, maliyet ve fiyatlama kararlarini onumuzdeki "
         "aylarda etkileyebilir.",
         "Yan projen icin fiyatlama veya yatirim zamanlamani bu veriye "
         "gore bir dakika gozden gecir."),
    ],
    "Gunun Firsat Yazilim Projeleri": [
        ([""],
         "Show HN'deki projeler genellikle 1-2 kisilik ekiplerin AI "
         "araclariyla hizlica hayata gecirdigi nise urunler.",
         "Bu projenin cozdugu problemin Turkce/yerel bir karsiligi yoksa, "
         "ayni fikri AI ile 2-3 haftada bir MVP olarak kodlayip kucuk bir "
         "kullanici kitlesine sunmayi degerlendir."),
    ],
}

DEFAULT_ANALYSIS = {
    "Teknoloji": ("Teknoloji dunyasinda urun ve girisim hareketliligi surekli devam ediyor.",
                  "Haberdeki urunun temel deger onerisini not al; benzer bir ihtiyaci "
                  "Turkiye'de dusuk maliyetle cozup cozemeyecegini degerlendir."),
    "Yapay Zeka": ("Yapay zeka araclari gundelik is sureclerine hizla entegre oluyor.",
                   "Bu araci dene; Nesine'deki veya tanidigin bir is surecine uygulanabilir "
                   "mi gor, uygulanabilirse kucuk bir otomasyon urunu olarak paketleyebilirsin."),
    "Dunya ve Jeopolitik": ("Kuresel gelismeler Turkiye'deki sektorleri (lojistik, enerji, "
                             "turizm, e-ticaret) dolayli yoldan etkileyebilir.",
                            "Bu gelismenin kendi yan projelerine bir risk ya da firsat olarak "
                            "yansiyip yansimadigini bir dakika dusun."),
    "Turkiyede Is Firsatlari": ("Bu gelisme, Turkiye pazarinda kisa vadede hareketlenecek bir "
                                 "alani isaret ediyor.",
                                "Bu firsati/trendi not al; 3-6 aylik girisim planinla kesisen bir "
                                "yani var mi degerlendir."),
    "Turkiye Guncel Ekonomik Haberleri": ("Bu veri/karar, maliyet ve fiyatlama kararlarini "
                                           "onumuzdeki aylarda etkileyebilir.",
                                          "Yan projen icin fiyatlama veya yatirim zamanlamani bu "
                                          "veriye gore bir dakika gozden gecir."),
    "Gunun Firsat Yazilim Projeleri": ("Show HN'deki projeler genellikle 1-2 kisilik ekiplerin AI "
                                        "araclariyla hizlica hayata gecirdigi nise urunler.",
                                       "Bu projenin cozdugu problemin Turkce/yerel bir karsiligi "
                                       "yoksa, ayni fikri AI ile 2-3 haftada bir MVP olarak kodlayip "
                                       "kucuk bir kullanici kitlesine sunmayi degerlendir."),
}


def build_analysis(category, items):
    text_blob = " ".join((it["title"] + " " + it["summary"]).lower() for it in items)
    for keywords, analysis, suggestion in ANALYSIS_RULES.get(category, []):
        if any(kw and kw in text_blob for kw in keywords):
            return analysis, suggestion
    return DEFAULT_ANALYSIS.get(category, (None, None))

INTRO_LINES = [
    "Gunaydin Mehmet, dunya gece de durmadi, iste bilmen gerekenler.",
    "Gunaydin! Bugun seni bekleyen gelismeler ve girisim firsatlari asagida.",
    "Yeni bir gun, yeni gelismeler. Iste son 24 saatin ozeti.",
]

# -----------------------------------------------------------------------
# Girisim fikirleri: haberlerden BAGIMSIZ, sabit bir havuz. Kullanici
# profiline gore secildi -> is gelistirme uzmani, Istanbul, Nesine'de
# calisiyor, tek basina + sadece AI araclariyla kurabilecegi, dusuk
# maliyet/bakim gerektiren ama buyume/kazanc potansiyeli yuksek fikirler.
# Her sabah gundeme gore (o gunku haber metnine gore) bu havuzdan en
# alakali olanlar one cikarilir, geri kalani rastgele secilir.
# -----------------------------------------------------------------------
PROFILE_IDEA_POOL = [
    (["yapay zeka", "ai", "otomasyon", "chatbot", "model"],
     "Nise AI Chatbot Hizmeti (Esnaf/KOBI Icin)",
     "Kucuk isletmelere (kuafor, diyetisyen, hukuk burosu vb.) WhatsApp "
     "uzerinden calisan, randevu alan ve sik sorulan sorulari yanitlayan "
     "AI chatbot kur. Tek bir no-code/low-code altyapi (ör. n8n + bir LLM "
     "API'si) ile aylik sabit ucretle onlarca musteriye satilabilir.",
     "Dusuk: Sunucu/API maliyeti aylik birkac dolar, bakim neredeyse sifir.",
     "Yuksek: Her musteri tekrarlayan aylik gelir, cok sayida isletmeye kopyalanabilir.",
     "Cevrendeki 5 esnafa WhatsApp'tan musteri sorularini kim yanitliyor diye sor."),
    (["e-ticaret", "ecommerce", "perakende", "trendyol", "hepsiburada"],
     "AI Destekli Urun Aciklamasi / Reklam Metni Araci",
     "Trendyol/Hepsiburada/Shopify saticilari icin, urun fotografindan "
     "otomatik SEO'lu aciklama ve reklam metni ureten basit bir web araci "
     "yap. Tek kisi tarafindan AI ile kodlanip aylik abonelikle satilabilir.",
     "Dusuk: Sadece API cagrisi maliyeti, sunucu yuku hafif.",
     "Yuksek: Binlerce kucuk satici potansiyel musteri, viral buyume sansi.",
     "Bir e-ticaret saticilar grubuna (Facebook/Telegram) katil, en cok "
     "sikayet edilen konuyu not al."),
    (["finans", "kur", "enflasyon", "faiz", "ekonomi"],
     "Freelancer/Esnaf Icin AI Mali Musavir Asistani",
     "Fatura/fis fotografini okuyup otomatik gelir-gider takibi ve basit "
     "vergi tahmini yapan bir mobil/web araci; AI OCR + basit kurallarla "
     "tek basina gelistirilebilir.",
     "Dusuk: Bulut OCR/LLM API maliyeti disinda ek yatirim gerekmiyor.",
     "Yuksek: Turkiye'de milyonlarca esnaf/freelancer hedef kitle, "
     "abonelik modeliyle olceklenir.",
     "3 freelancer arkadasina gelir-gider takibini nasil yaptigini sor."),
    (["egitim", "ogrenci", "universite", "sinav", "dil ogren"],
     "AI ile Kisisellestirilmis Sinav/Dil Kocu",
     "YKS/KPSS/yabanci dil gibi dar bir sinav turunde, AI ile kisiye ozel "
     "soru ureten ve zayif konulari tespit eden bir web/app araci; "
     "icerik uretimini tamamen AI yapar, sen sadece urunu kurgularsin.",
     "Dusuk: Icerik uretim maliyeti AI ile neredeyse sifir, sunucu hafif.",
     "Yuksek: Buyuk ve surekli yenilenen ogrenci kitlesi, abonelik + "
     "reklam geliri potansiyeli.",
     "Bir ogrenci Telegram/Discord grubuna gir, en cok sorulan soruyu "
     "not al."),
    (["saglik", "wellness", "diyet", "fitness"],
     "AI Destekli Kisisel Saglik/Beslenme Takip Araci",
     "Yemek fotografindan kalori/makro tahmini yapan, AI ile kisisel "
     "oneriler sunan basit bir mobil uygulama; gorsel tanima + LLM "
     "API'leriyle tek basina kurulabilir.",
     "Dusuk: API tabanli, kendi sunucunu buyutmene gerek yok.",
     "Yuksek: Saglik/fitness app pazari buyuk ve surekli buyuyor, "
     "abonelik modeli kanitlanmis.",
     "App Store'da bu kategoride en cok sikayet edilen 3 uygulamayi "
     "incele, eksiklerini not al."),
    (["emlak", "kira", "konut"],
     "AI Destekli Kira/Emlak Karsilastirma Araci",
     "Bolgeye gore kira/satis fiyatlarini AI ile analiz edip adil fiyat "
     "tahmini sunan bir web araci; acik veri + basit bir model ile tek "
     "basina kurulabilir, reklam veya premium rapor ile gelir uretir.",
     "Dusuk: Veri toplama otomatik, sunucu maliyeti dusuk.",
     "Yuksek: Turkiye'de kira/emlak gundemde kaldigi surece trafik potansiyeli yuksek.",
     "Sahibinden/Hepsiemlak'tan 20 ilan cekip fiyat farkliliklarini incele."),
    (["lojistik", "kargo", "tedarik"],
     "Kucuk Isletmeler icin AI Stok/Siparis Tahmin Araci",
     "Kucuk e-ticaret/perakende isletmeleri icin gecmis satis verisinden "
     "AI ile stok tukenme tahmini yapan basit bir dashboard; tek basina "
     "AI ile kodlanip aylik abonelikle satilabilir.",
     "Dusuk: Hafif bir web uygulamasi, veri isleme maliyeti dusuk.",
     "Yuksek: Stoksuz kalma/asiri stok kaybini azalttigi icin net ROI "
     "gosterilebilir, satisi kolaylasir.",
     "2-3 kucuk e-ticaret satici ile konusup stok yonetimini nasil "
     "yaptiklarini sor."),
    (["icerik", "sosyal medya", "pazarlama", "reklam"],
     "Tek Kisilik AI Icerik/Sosyal Medya Ajansi",
     "Kucuk isletmelere, tamamen AI araclariyla (metin + gorsel + video "
     "script) aylik sosyal medya icerigi ureten bir hizmet; musteri "
     "basina haftada birkac saat is, AI cogu isi yapar.",
     "Dusuk: Arac maliyeti aylik sabit, ek personel gerekmiyor.",
     "Yuksek: Her musteri tekrarlayan gelir, zamanla portfoyle buyur.",
     "3 esnafa sosyal medya yonetimini kime/nasil yaptirdigini sor, "
     "fiyat teklifi hazirla."),
]


def _to_utc_struct_cutoff(hours):
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _entry_datetime(entry):
    for field in ("published_parsed", "updated_parsed"):
        value = getattr(entry, field, None)
        if value:
            return datetime.fromtimestamp(timegm(value), tz=timezone.utc)
    return None


def fetch_category_items(sources, seen_titles, limit=ITEMS_PER_CATEGORY, window_hours=WINDOW_HOURS):
    cutoff = _to_utc_struct_cutoff(window_hours)
    items = []
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
            title_key = title.lower()
            if not title or title_key in seen_titles:
                continue
            entry_dt = _entry_datetime(entry)
            if entry_dt is not None and entry_dt < cutoff:
                continue
            seen_titles.add(title_key)
            link = getattr(entry, "link", "")
            summary = _clean_summary(getattr(entry, "summary", "") or getattr(entry, "description", ""))
            items.append({"title": title, "link": link, "summary": summary, "source": source_name})
        if len(items) >= limit:
            break
    if not items:
        # Zaman penceresinde hic haber yoksa, bos birakmak yerine en guncel
        # birkac basligi (tarihe bakmadan) goster.
        return fetch_category_items(sources, seen_titles, limit=limit, window_hours=24 * 7)
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
    """Haberlerden BAGIMSIZ, profile gore kurate edilmis havuzdan fikir secer.
    O gunun gundemiyle (haber metniyle) eslesen anahtar kelimeli fikirler
    varsa once onlar, kalan slotlar rastgele doldurulur -> boylece "gundem
    ne ise girisim fikri de o yonde" olur ama fikrin kendisi haberden
    turetilmez, sabit/kurate edilmis havuzdandir."""
    text_blob = " ".join((it["title"] + " " + it["summary"]).lower() for it in all_items)

    gundemle_eslesen = []
    diger = []
    for keywords, name, desc, maliyet, potansiyel, first_step in PROFILE_IDEA_POOL:
        entry = (name, desc, maliyet, potansiyel, first_step)
        if any(kw in text_blob for kw in keywords):
            gundemle_eslesen.append(entry)
        else:
            diger.append(entry)

    rng.shuffle(gundemle_eslesen)
    rng.shuffle(diger)
    ideas = (gundemle_eslesen + diger)[:count]
    return ideas


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

        analysis, suggestion = build_analysis(category, items)
        title_tr = CATEGORY_TITLES_TR.get(category, category)

        analysis_html = ""
        if analysis:
            analysis_html = (
                "<div style='background:#f0f6ff; border-left:4px solid #1a73e8; "
                "padding:10px 14px; font-size:13px; color:#333;'>"
                f"<b>Analiz:</b> {analysis}<br><b>Onerim:</b> {suggestion}</div>"
            )

        sections_html.append(f"""
        <h2 style="font-size:18px; color:#222; border-bottom:2px solid #eee; padding-bottom:6px; margin-top:28px;">{title_tr}</h2>
        <ul style="list-style:none; padding-left:0;">{headline_html}</ul>
        {analysis_html}
        """)

    ideas = generate_startup_ideas(all_items, rng)
    ideas_html = ""
    for name, desc, maliyet, potansiyel, first_step in ideas:
        ideas_html += f"""
        <div style="background:#fff8e6; border-left:4px solid #f5a623; padding:12px 14px; margin-bottom:14px; border-radius:4px;">
          <div style="font-weight:700; font-size:15px; color:#222;">{name}</div>
          <div style="color:#444; font-size:13px; margin-top:4px;">{desc}</div>
          <div style="color:#666; font-size:12px; margin-top:6px;"><b>Maliyet/Bakim:</b> {maliyet}</div>
          <div style="color:#666; font-size:12px; margin-top:2px;"><b>Buyume/Kazanc Potansiyeli:</b> {potansiyel}</div>
          <div style="color:#b35c00; font-size:13px; margin-top:6px;"><b>Ilk adim:</b> {first_step}</div>
        </div>"""

    ideas_section = f"""
    <h2 style="font-size:18px; color:#222; border-bottom:2px solid #eee; padding-bottom:6px; margin-top:32px;">Girisim Firsatlari (Tek Basina + Sadece AI ile)</h2>
    <p style="color:#555; font-size:13px;">Profiline gore kurate edilmis, dusuk maliyet/bakim gerektiren ama buyume ve kazanc potansiyeli yuksek, 3-6 ay icinde tek basina ve AI araclariyla hayata gecirebilecegin fikirler:</p>
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
    mail_to_list = os.environ.get("MAIL_TO_LIST", os.environ.get("MAIL_TO", gmail_user))
    
    # Virgülle ayrılmış listeyi parse et
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
    
    print(f"Mail {len(recipients)} kişiye gonderildi: {', '.join(recipients)}")


def main():
    tz = ZoneInfo("Europe/Istanbul")
    now = datetime.now(tz)

    categories_data = {}
    all_items = []
    seen_titles = set()
    for category, sources in FEEDS.items():
        items = fetch_category_items(sources, seen_titles)
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
