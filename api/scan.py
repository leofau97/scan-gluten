from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def analyze(product_data=None, barcode=None):
    if product_data and product_data.get("ingredients"):
        prompt = f"""Sei un esperto di celiachia. Analizza per un celiaco.
PRODOTTO: {product_data.get('name', '')}
MARCA: {product_data.get('brand', '')}
INGREDIENTI: {product_data.get('ingredients', '')}
ALLERGENI: {product_data.get('allergens', '')}

Rispondi SOLO in JSON:
{{"prodotto":"{product_data.get('name','')}","marca":"{product_data.get('brand','')}","sicuro":true,"livello":"verde","analisi":"spiegazione breve","ingredienti_pericolosi":[],"ingredienti_sospetti":[],"conservanti_rischiosi":[],"ingredienti_sicuri":[],"avviso_contaminazione":null}}

REGOLE:
- sicuro=true SOLO se zero glutine
- Pericolosi: frumento grano orzo segale farro malto glutine
- Sospetti: amido non specificato aromi naturali proteine vegetali idrolizzate
- Se "tracce di glutine": sicuro=false livello=giallo
- Solo JSON nessun testo"""
    else:
        prompt = f"""Prodotto con barcode {barcode}. Analizza per celiaci.
Rispondi SOLO in JSON:
{{"prodotto":"Prodotto {barcode}","marca":"","sicuro":false,"livello":"giallo","analisi":"Prodotto non trovato nel database. Verifica gli ingredienti sull etichetta.","ingredienti_pericolosi":[],"ingredienti_sospetti":[],"conservanti_rischiosi":[],"ingredienti_sicuri":[],"avviso_contaminazione":null}}"""

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
            clean = text.replace("```json","").replace("```","").strip()
            start = clean.find('{')
            end = clean.rfind('}') + 1
            if start >= 0 and end > start:
                clean = clean[start:end]
            result = json.loads(clean)
            result.setdefault("analisi", "Analisi completata.")
            result.setdefault("ingredienti_pericolosi", [])
            result.setdefault("ingredienti_sospetti", [])
            result.setdefault("conservanti_rischiosi", [])
            result.setdefault("ingredienti_sicuri", [])
            result.setdefault("avviso_contaminazione", None)
            return result

    except Exception as e:
        return {"error": str(e), "prodotto": "Errore", "sicuro": False, "livello": "rosso", "analisi": str(e), "ingredienti_pericolosi": [], "ingredienti_sospetti": [], "conservanti_rischiosi": [], "ingredienti_sicuri": [], "avviso_contaminazione": None}


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
            result = analyze(product_data=product_data, barcode=barcode)
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
