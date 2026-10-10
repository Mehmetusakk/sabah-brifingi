#!/usr/bin/env python3
"""
Her sabah 09:00'da 20 ingilizce kelime (4 kategori x 5 kelime) gonderir.
Her kelime icin: tanimlama, ornek cumleler, farkli alanlarda kullanimi.
Kategoriler her gun degisir (rastgele secilir).
"""

import os
import random
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

# Kelime havuzu: kategori -> [(kelime, tur, tanim, {alan: cumle, ...}), ...]
WORD_POOL = {
    "Business & Professional": [
        ("Leverage", "verb/noun", "Bir avantajı maksimum etki icin kullanmak; finansal borçlanma",
         {"Business": "We can leverage our existing customer base to expand into new markets.",
          "Finance": "The company used leverage to finance the acquisition.",
          "Technology": "Developers leverage open-source libraries to speed up development."}),
        ("Synergy", "noun", "Iki veya daha fazla seyin birlikte calistiginda ortaya cikan ek deger",
         {"Business": "The merger created significant synergy between the two departments.",
          "Science": "There is a synergy between exercise and proper nutrition for health.",
          "Team": "Good team synergy leads to better project outcomes."}),
        ("Paradigm", "noun", "Bir alanin temel varsayimlari ve yontemleri; bir ornek veya model",
         {"Science": "Einstein's theory represented a paradigm shift in physics.",
          "Business": "The company adopted a new paradigm for customer service.",
          "Education": "Digital learning is changing the educational paradigm."}),
        ("Stakeholder", "noun", "Bir projenin veya sirketin sonucundan etkilenen kisi veya grup",
         {"Business": "We need to consult all stakeholders before making this decision.",
          "Politics": "Environmental stakeholders are concerned about the new policy.",
          "Project": "Stakeholder engagement is critical for project success."}),
        ("Scalable", "adjective", "Buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutulup buyutilir",
         {"Technology": "The cloud infrastructure is highly scalable to handle traffic spikes.",
          "Business": "Our business model is scalable and can grow without proportional cost increases.",
          "Software": "The application uses a scalable architecture for handling millions of users."}),
    ],
    "Academic & Intellectual": [
        ("Empirical", "adjective", "Gozlem ve deneyime dayanan; teoriye degil, gercek verilere dayanan",
         {"Science": "The study provides empirical evidence for the hypothesis.",
          "Research": "Empirical data shows a strong correlation between variables.",
          "Philosophy": "Empirical knowledge comes from direct experience, not reasoning alone."}),
        ("Hypothesis", "noun", "Bir arastirmada test edilecek onerilen aciklama veya tahmin",
         {"Science": "The researcher formulated a hypothesis before conducting the experiment.",
          "Medicine": "The hypothesis suggests that the drug reduces inflammation.",
          "Psychology": "Our hypothesis is that stress affects memory retention."}),
        ("Methodology", "noun", "Bir arastirma veya projedeki sistematik yontem ve prosedurler",
         {"Research": "The study's methodology was rigorous and well-documented.",
          "Education": "Different teaching methodologies produce different learning outcomes.",
          "Business": "We need to review our project methodology for efficiency."}),
        ("Correlation", "noun", "Iki seyin birlikte degisme derecesi; iliskili olma durumu",
         {"Statistics": "There is a strong positive correlation between study hours and test scores.",
          "Science": "The correlation between temperature and reaction rate is well-established.",
          "Economics": "Economists study the correlation between inflation and unemployment."}),
        ("Ambiguous", "adjective", "Birden fazla anlama gelebilecek; belirsiz, muphemm",
         {"Communication": "The instructions were ambiguous, leading to confusion.",
          "Law": "Ambiguous contract language can cause disputes.",
          "Writing": "Good writing avoids ambiguous pronouns and references."}),
    ],
    "Travel & Culture": [
        ("Itinerary", "noun", "Bir yolculugun plani; ziyaret edilecek yerler ve zamanlar",
         {"Travel": "Our itinerary includes visits to three countries in two weeks.",
          "Tourism": "The tour operator provided a detailed itinerary for the group.",
          "Business": "The executive's itinerary was packed with meetings and events."}),
        ("Cuisine", "noun", "Bir bolgenin veya ulkenin yemek tarzı ve yemekleri",
         {"Food": "French cuisine is known for its sophisticated techniques.",
          "Travel": "One of the highlights of the trip was experiencing local cuisine.",
          "Culture": "Thai cuisine balances sweet, sour, salty, and spicy flavors."}),
        ("Heritage", "noun", "Gecmisten gelen kültür, gelenek, ve tarihsel miras",
         {"Culture": "The city's architectural heritage is protected by law.",
          "History": "Indigenous heritage is an important part of national identity.",
          "Tourism": "UNESCO World Heritage sites attract millions of visitors annually."}),
        ("Expedition", "noun", "Bir amac icin yapilan, genellikle uzun ve zor bir yolculuk",
         {"Adventure": "The Arctic expedition took six months to complete.",
          "History": "Early explorers undertook dangerous expeditions to discover new lands.",
          "Science": "The research expedition collected samples from remote locations."}),
        ("Picturesque", "adjective", "Resim gibi guzel; gorsel olarak cekilebilir kadar guzel",
         {"Travel": "The picturesque village was a perfect destination for photographers.",
          "Literature": "The author described the landscape in picturesque detail.",
          "Tourism": "Picturesque coastal towns attract thousands of tourists each summer."}),
    ],
    "Science & Nature": [
        ("Biodiversity", "noun", "Bir bolgedeki farkli bitki ve hayvan turleri cokluğu",
         {"Ecology": "Rainforests have incredible biodiversity with millions of species.",
          "Conservation": "Protecting biodiversity is crucial for ecosystem health.",
          "Environment": "Climate change threatens global biodiversity."}),
        ("Photosynthesis", "noun", "Bitkiler tarafindan ışık enerjisini kimyasal enerjiye cevirmek",
         {"Biology": "Photosynthesis is the process by which plants produce glucose.",
          "Chemistry": "The photosynthesis equation shows how water and CO2 are converted.",
          "Environment": "Photosynthesis is essential for producing oxygen in the atmosphere."}),
        ("Ecosystem", "noun", "Bir bolgedeki canli organizmalar ve onlarin cevre ile iliskisi",
         {"Ecology": "A healthy ecosystem requires balance between predators and prey.",
          "Conservation": "Wetland ecosystems provide habitat for many species.",
          "Science": "Coral reef ecosystems are among the most biodiverse on Earth."}),
        ("Mutation", "noun", "DNA'da meydana gelen degisiklik; genetik degisim",
         {"Biology": "Genetic mutations can lead to evolution over generations.",
          "Medicine": "Some mutations increase the risk of certain diseases.",
          "Genetics": "Random mutations are the source of genetic variation."}),
        ("Phenomenon", "noun", "Gozlemlenebilir bir olay veya durum; ilginc bir olay",
         {"Science": "The aurora borealis is a natural phenomenon caused by solar wind.",
          "Psychology": "The placebo effect is a well-documented psychological phenomenon.",
          "Physics": "Quantum entanglement is a fascinating phenomenon in physics."}),
    ],
    "Finance & Economics": [
        ("Inflation", "noun", "Mal ve hizmetlerin fiyatlarinin zaman icinde artmasi",
         {"Economics": "High inflation erodes the purchasing power of consumers.",
          "Finance": "Central banks try to control inflation through interest rates.",
          "Business": "Companies must adjust prices to account for inflation."}),
        ("Portfolio", "noun", "Yatirimci tarafindan tutulan cesitli yatirimlar; calismalarin koleksiyonu",
         {"Finance": "A diversified portfolio reduces investment risk.",
          "Art": "The artist's portfolio showcases her best work.",
          "Business": "The company's product portfolio includes software and services."}),
        ("Volatility", "noun", "Hizli ve buyuk degisimler; istikrarsizlik",
         {"Finance": "Stock market volatility increased during the economic crisis.",
          "Weather": "Climate volatility is affecting agricultural production.",
          "Business": "Currency volatility impacts international trade."}),
        ("Dividend", "noun", "Bir sirketin karinin hissedarlarına dagitilan kismi",
         {"Finance": "The company announced a quarterly dividend of $0.50 per share.",
          "Investment": "Dividend-paying stocks provide regular income to investors.",
          "Business": "The board decided to increase dividends for shareholders."}),
        ("Recession", "noun", "Ekonomide uzun sureli buyume dusmesi; ekonomik daralma",
         {"Economics": "The country entered a recession after the financial crisis.",
          "Business": "Many companies laid off employees during the recession.",
          "Finance": "Investors often move to safer assets during a recession."}),
    ],
}


def select_words_for_day(day_seed, words_per_category=5, num_categories=4):
    """Gunu temel alan rastgele kategori ve kelime secimi."""
    rng = random.Random(day_seed)
    
    # 4 kategori sec
    all_categories = list(WORD_POOL.keys())
    selected_categories = rng.sample(all_categories, min(num_categories, len(all_categories)))
    
    # Her kategori icin 5 kelime sec
    words_by_category = {}
    for category in selected_categories:
        words = WORD_POOL[category]
        selected = rng.sample(words, min(words_per_category, len(words)))
        words_by_category[category] = selected
    
    return words_by_category


def build_email_html(words_by_category):
    """HTML mail olustur."""
    sections_html = []
    
    for category, words in words_by_category.items():
        words_html = ""
        for word, word_type, definition, examples in words:
            examples_html = ""
            for field, sentence in examples.items():
                examples_html += f"<div style='margin-left:20px; margin-top:6px;'><span style='color:#666; font-weight:600;'>{field}:</span> <em>{sentence}</em></div>"
            
            words_html += f"""
            <div style="background:#f9f9f9; border-left:4px solid #4285f4; padding:12px 14px; margin-bottom:12px; border-radius:4px;">
              <div style="font-weight:700; font-size:16px; color:#1a73e8;">{word}</div>
              <div style="color:#666; font-size:12px; margin-top:2px;"><em>({word_type})</em></div>
              <div style="color:#333; font-size:13px; margin-top:6px;"><b>Tanim:</b> {definition}</div>
              <div style="color:#333; font-size:13px; margin-top:8px;"><b>Ornek Cumleler:</b></div>
              {examples_html}
            </div>"""
        
        sections_html.append(f"""
        <h2 style="font-size:18px; color:#222; border-bottom:2px solid #eee; padding-bottom:6px; margin-top:28px;">{category}</h2>
        {words_html}
        """)
    
    html = f"""
    <html>
    <body style="font-family: -apple-system, Helvetica, Arial, sans-serif; max-width:640px; margin:0 auto; padding:20px; color:#222;">
      <h1 style="font-size:22px;">Daily English Words</h1>
      <p style="color:#555; font-size:14px;">Bugun ogrenmek icin 20 ingilizce kelime. Her kelime icin tanim, ornek cumleler ve farkli alanlarda kullanimi.</p>
      {"".join(sections_html)}
      <p style="color:#aaa; font-size:12px; margin-top:32px;">Bu mail her sabah otomatik olarak gonderilir. Kategoriler her gun degisir.</p>
    </body>
    </html>
    """
    return html


def send_email(html_body, subject):
    """Mail gonder."""
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
    
    print(f"Mail {len(recipients)} kişiye gonderildi: {', '.join(recipients)}")


def main():
    tz = ZoneInfo("Europe/Istanbul")
    now = datetime.now(tz)
    day_seed = now.strftime("%Y%m%d")
    
    words_by_category = select_words_for_day(day_seed)
    html = build_email_html(words_by_category)
    subject = f"Daily English Words - {now.strftime('%d %B %Y')}"
    send_email(html, subject)
    print("Mail gonderildi:", subject)


if __name__ == "__main__":
    main()
