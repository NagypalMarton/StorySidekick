from flask import Flask, render_template
from flask_socketio import SocketIO, send
from transformers import pipeline
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# NLP pipeline inicializálása (huBERT)
hubert_pipe = pipeline("text-classification", model="SZTAKI-HLT/hubert-base-cc")
# NLP pipeline inicializálása (Bert2Bert summarization)
summarizer = pipeline("summarization", model="SZTAKI-HLT/Bert2Bert-HunSum-1")

# Példa könyvadatbázis
books = {
    "xyz": {
        "title": "XyZ",
        "desc": "A XyZ egy izgalmas magyar regény, amely a barátságról és bátorságról szól. A történet főhőse egy fiatal lány, aki különleges kalandokba keveredik.",
        "rating": 4.5
    },
    # Ide vehetsz fel több könyvet
}

MOLY_API_KEY = "4f7679f7ec5f95a5c7f08da35c79df1b"
MOLY_SEARCH_URL = "https://moly.hu/api/books.json"
MOLY_BOOK_URL = "https://moly.hu/api/book/{id}.json"
MOLY_REVIEWS_URL = "https://moly.hu/api/book_reviews/{id}.json"

def get_book_from_moly(query):
    params = {"q": query, "key": MOLY_API_KEY}
    resp = requests.get(MOLY_SEARCH_URL, params=params)
    if resp.status_code == 200 and resp.json().get("books"):
        return resp.json()["books"][0]  # első találat
    return None

def get_book_details(book_id):
    url = MOLY_BOOK_URL.format(id=book_id)
    resp = requests.get(url, params={"key": MOLY_API_KEY})
    if resp.status_code == 200:
        return resp.json()
    return None

def get_book_reviews(book_id):
    url = MOLY_REVIEWS_URL.format(id=book_id)
    resp = requests.get(url, params={"key": MOLY_API_KEY})
    if resp.status_code == 200 and resp.json().get("reviews"):
        return resp.json()["reviews"]
    return []

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(msg):
    # NLP válasz generálása
    try:
        nlp_result = hubert_pipe(msg)
        nlp_response = nlp_result[0]['label'] if nlp_result else "(Nincs válasz)"
    except Exception as e:
        nlp_response = f"(NLP hiba: {e})"
    send(f"Felhasználó: {msg}", broadcast=True)
    send(f"Bot: {nlp_response}", broadcast=True)
    # Könyvnév keresés a felhasználó üzenetében
    found = None
    for key, book in books.items():
        if book["title"].lower() in msg.lower():
            found = book
            break
    if found:
        # Könyv leírás összegzése
        summary = summarizer(found["desc"], max_length=60, min_length=10, do_sample=False)[0]['summary_text']
        response = f"{found['title']} (Értékelés: {found['rating']}): {summary}"
    else:
        response = "Nem találtam ilyen könyvet az adatbázisban."
    send(f"Felhasználó: {msg}", broadcast=True)
    send(f"Bot: {response}", broadcast=True)
    # Könyv keresése a moly.hu-n
    book = get_book_from_moly(msg)
    if book:
        book_id = book["id"]
        details = get_book_details(book_id)
        desc = details.get("description", "Nincs leírás.") if details else "Nincs leírás."
        # Értékelések lekérése a könyv ID alapján
        reviews = get_book_reviews(book_id)
        # Összegzés generálása CSAK ha van leírás és az nem None vagy üres
        if desc and isinstance(desc, str) and desc.strip():
            try:
                summary = summarizer(desc, max_length=60, min_length=10, do_sample=False)[0]['summary_text']
            except Exception as e:
                summary = f"(Összegzés hiba: {e})"
        else:
            summary = "Nincs összegzés."
        # Értékelésekből egy rövid összefoglaló CSAK ha van értékelés
        review_texts = [r.get("text", "") for r in reviews[:3] if r.get("text")]
        if review_texts:
            try:
                review_summary = summarizer(" ".join(review_texts), max_length=60, min_length=10, do_sample=False)[0]['summary_text']
            except Exception as e:
                review_summary = f"(Értékelés összegzés hiba: {e})"
        else:
            review_summary = "Nincs értékelés."
        response = f"Cím: {book['title']}\nSzerző: {book['author']}\nÖsszefoglaló: {summary}\nOlvasói vélemények: {review_summary}"
    else:
        response = f"Nem találtam ilyen könyvet a moly.hu-n: {msg}"
    send(f"Felhasználó: {msg}", broadcast=True)
    send(f"Bot: {response}", broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
