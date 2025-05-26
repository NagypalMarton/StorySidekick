from flask import Flask, render_template
from flask_socketio import SocketIO, send
from transformers import pipeline
import requests
import re
from html import unescape

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# NLP pipeline inicializálása (huBERT)
hubert_pipe = pipeline("text-classification", model="SZTAKI-HLT/hubert-base-cc")
# NLP pipeline inicializálása (huBERT QA)
qa_pipeline = pipeline(
    "question-answering",
    model="mcsabai/huBert-fine-tuned-hungarian-squadv2",
    tokenizer="mcsabai/huBert-fine-tuned-hungarian-squadv2",
    topk=1,
    handle_impossible_answer=True
)

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

def extract_title_from_prompt(prompt):
    # Egyszerű regex: idézőjelek vagy cím kulcsszó után
    match = re.search(r'"([^"]+)"|című ([^\?\.,]+)', prompt, re.IGNORECASE)
    if match:
        if match.group(1):
            return match.group(1)
        elif match.group(2):
            return match.group(2).strip()
    return prompt  # fallback: teljes prompt

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(msg):
    # Könyvcím kinyerése a user promptból
    title = extract_title_from_prompt(msg)
    # Ha nem sikerült értelmes címet kinyerni, kérdezzen vissza
    if not title or title.strip() == msg.strip():
        response = "Kérlek, add meg pontosan a könyv címét idézőjelben vagy a 'című' szóval! Példa: Milyen a 'Vándorünnep'?"

        send(f"Felhasználó: {msg}", broadcast=True)
        send(f"Bot: {response}", broadcast=True)
        return
    # 1. Könyv keresése a moly.hu-n (cím alapján)
    book = get_book_from_moly(title)
    if book:
        # Szerző nevét a részletes adatokból próbáljuk kinyerni, ha van
        book_id = book["id"]
        details = get_book_details(book_id)
        # Szerző kinyerése a részletes adatokból (authors lista)
        author = "Ismeretlen szerző"
        if details and "authors" in details and details["authors"]:
            author = details["authors"][0].get("name", author)
        else:
            author = book.get("author", author)
        desc = None
        # Próbáljuk a description-t több helyről is kinyerni
        if details:
            # 1. Próbáljuk a 'description' mezőt
            desc = details.get("description")
            # 2. Ha nincs vagy üres, próbáljuk a 'book' kulcs alatt (néha így is előfordulhat)
            if (not desc or not desc.strip()) and "book" in details and isinstance(details["book"], dict):
                desc = details["book"].get("description")
            # 3. Ha még mindig nincs, próbáljuk a 'subtitle'-t vagy más mezőt
            if (not desc or not desc.strip()):
                desc = details.get("subtitle", "")
        if not desc or not isinstance(desc, str) or not desc.strip():
            desc = "Nincs leírás."
        else:
            desc = unescape(desc)
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = desc.strip()
        # 3. QA modell használata a leírás alapján
        if desc and desc != "Nincs leírás.":
            try:
                # Fix, összefoglaló kérdés a QA pipeline-hoz
                summary_question = "Foglalj össze mindent, amit tudni lehet erről a könyvről!"
                qa_results = qa_pipeline({
                    'context': desc,
                    'question': summary_question
                }, topk=3)
            except Exception as e:
                qa_results = []
                answer = f"(QA hiba: {e})"
            if isinstance(qa_results, list) and qa_results:
                # Mondatonkénti deduplikálás, természetesebb válasz
                all_answers = ' '.join([r['answer'] for r in qa_results if r.get('answer') and r['answer'] != ''])
                # Mondatok szétvágása, whitespace tisztítás
                sentences = re.split(r'(?<=[.!?]) +', all_answers)
                seen = set()
                unique_sentences = []
                for s in sentences:
                    s_clean = s.strip()
                    if s_clean and s_clean not in seen:
                        seen.add(s_clean)
                        unique_sentences.append(s_clean)
                answer = ' '.join(unique_sentences) if unique_sentences else '(Nincs válasz)'
            elif isinstance(qa_results, dict):
                answer = qa_results.get('answer', '(Nincs válasz)')
        else:
            answer = "Nincs leírás a könyvhöz."
        response = f"Cím: {details.get('title', book.get('title', 'Ismeretlen'))}\nSzerző: {author}\nIsmertető: {answer}"
    else:
        response = f"Nem találtam ilyen könyvet a moly.hu-n: {title}"
    send(f"Felhasználó: {msg}", broadcast=True)
    send(f"Bot: {response}", broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
