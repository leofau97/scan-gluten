from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.parse

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def analyze_ingredients(product_data=None, barcode=None):
    """Analizza ingredienti con Groq."""
    
    if product_data and product_data.get("ingredients"):
        prompt = f"""Sei un esperto di celiachia. Analizza questi ingredienti per un celiaco.

PRODOTTO: {product_data.get('name', 'Sconosciuto')}
MARCA: {product_data.get('brand', '')}
INGREDIENTI: {product_data.get('ingredients', '')}
ALLERGENI: {product_data.get('allergens', '')}

Rispondi SOLO in JSON:
{{
  "prodotto": "nome prodotto",
  "marca": "marca",
  "sicuro": true o false,
  "livello": "verde o giallo o rosso",
  "analisi": "spiegazione breve in italiano max 2 righe",
  "ingredienti_pericolosi": [],
  "ingredienti_sospetti": [],
  "conservanti_rischiosi": [],
  "ingredienti_sicuri": [],
  "avviso_contaminazione": null
}}

REGOLE:
- sicuro=true SOLO se zero dubbi
- Pericolosi: frumento, grano, orzo, segale, farro, kamut, malto, glutine
- Sospetti: amido non specificato, aromi naturali, proteine vegetali idrolizzate, destrina, sciroppo glucosio non specificato
- Se vedi "puo contenere tracce": sicuro=false, livello=giallo
- Solo JSON, nessun altro testo"""

    elif barcode:
        prompt = f"""Sei un esperto di celiachia. Il codice a barre e: {barcode}
Se conosci il prodotto analizza i suoi ingredienti per un celiaco.
Se non lo conosci dillo nell analisi.

Rispondi SOLO in JSON:
{{
  "prodotto": "nome se lo conosci",
  "marca": "marca se la conosci",
  "sicuro": false,
  "livello": "giallo",
  "analisi": "Se non conosci il prodotto scrivi: Prodotto non trovato nel database. Cerca gli ingredienti sull etichetta e usali per una nuova analisi.",
  "ingredienti_pericolosi": [],
  "ingredienti_sospetti": [],
  "conservanti_rischiosi": [],
  "ingredienti_sicuri": [],
  "avviso_contaminazione": null
}}
Solo JSON, nessun altro testo."""
    else:
        return {"error": "Nessun dato fornito"}

    try:
        payload = json.dumps({
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 800,
            "temperature": 0.1
        }).encode()

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            text = data["choices"][0]["message"]["content"]
            clean = text.replace("```json", "").replace("```", "").strip()
            start = clean.find('{')
            end = clean.rfind('}') + 1
            if start >= 0 and end > start:
                clean = clean[start:end]
            return json.loads(clean)

    except Exception as e:
        return {"error": str(e)}


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))

            barcode = body.get("barcode")
            product_data = body.get("product_data")

            result = analyze_ingredients(
                product_data=product_data,
                barcode=barcode
            )

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        pass
