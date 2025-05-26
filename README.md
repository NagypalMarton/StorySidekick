# StorySidekick 📖🤖
**StorySidekick** egy magyar nyelvű könyvajánló chatbot, amely **Flask**-et és **huBERT** NLP-t használ.

## 🚀 Telepítés
1️⃣ Klónozd a repót: ```bash git clone https://github.com/NagypalMarton/StorySidekick.git cd StorySidekick
```

## StorySidekick – Magyar könyvajánló chatbot

Ez egy Flask + Bootstrap alapú magyar nyelvű chatalkalmazás, amely könyvajánló chatbotként működik. A felhasználó könyvcímre vagy kérdésre választ kap a moly.hu API-ból lekért könyvleírás alapján, természetes nyelvi válasszal.

### Fő funkciók

- **Valós idejű chat** Flask-SocketIO-val
- **Könyvcím kinyerése** a felhasználói promptból (idézőjelek vagy „című” szó alapján)
- **moly.hu API integráció**: könyv keresése cím alapján, szerző és leírás lekérése
- **Leírás tisztítása** HTML tagoktól, whitespace-től
- **QA modell**: mcsabai/huBert-fine-tuned-hungarian-squadv2 pipeline, fix összefoglaló kérdéssel
- **Válasz deduplikálása**: a QA pipeline topk=3 válaszait mondatonként deduplikálja, így természetesebb, informatívabb ismertetőt ad
- **Hibakezelés**: ha nincs találat vagy leírás, megfelelő üzenet

### Használat

1. Telepítsd a szükséges csomagokat:

   ```sh
   pip install flask flask-socketio transformers torch requests
   ```

1. Indítsd el az alkalmazást:

   ```sh
   python app.py
   ```

1. Nyisd meg a böngészőben: [http://localhost:5000](http://localhost:5000)

### Példák

- `Milyen a "Vándorünnep"?`
- `Miről szól a Holt költők társasága című könyv?`

### Működés

1. A felhasználó beír egy könyvcímet vagy kérdést.
2. A chatbot regex-szel kinyeri a könyvcímet.
3. Lekéri a moly.hu API-ból a könyv szerzőjét és leírását.
4. A leírást megtisztítja a HTML tagoktól.
5. A QA pipeline-hoz fix kérdést ad: „Foglalj össze mindent, amit tudni lehet erről a könyvről!”
6. A QA pipeline topk=3 válaszait mondatonként deduplikálja, majd összefűzi.
7. A válasz természetes, informatív ismertetőként jelenik meg a chatben.

### Hibakezelés

- Ha nem sikerül könyvcímet kinyerni, visszakérdez.
- Ha nincs találat vagy leírás, megfelelő üzenetet ad vissza.

### További fejlesztési lehetőségek

- Több szerző, alternatív címek kezelése
- Hosszabb leírások feldarabolása
- Válaszminőség további javítása (pl. summarization pipeline integrálása)

---

**Készítette:** [A projekt fejlesztője]
