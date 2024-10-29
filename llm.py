import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

PROMPT = """Sei un esperto agente immobiliare digitale per un chatbot dedicato alla ricerca di opportunità immobiliari interessanti.
Istruzioni:

Convertire il seguente JSON in una descrizione naturale e neutrale che presenti l’immobile in modo conciso ma completo. Sii chiaro e usa toni neutri e obiettivi, concentrandoti su informazioni rilevanti per un potenziale acquirente, come prezzo, posizione, caratteristiche principali e vantaggi dell'immobile.
Obiettivo:

Fornire un messaggio informativo e diretto che includa tutti i dettagli significativi, come se stessi parlando direttamente con un cliente interessato. La descrizione deve risultare fluida, leggibile ma neutra.

Esempio di risposta attesa: “Trilocale in buono stato al 4° piano, situato in Via Piazzi 61 nel quartiere San Carlo All'Arena di Napoli. Composto da 3 locali su 110 m², offre due camere da letto, cucina angolo cottura, bagno, balcone e terrazzo. Prezzo di vendita: €230.000. Spese condominiali: €40/mese. Palazzina del 1950 senza ascensore, doppia esposizione e infissi esterni in vetro/PVC."

Dati JSON:

{json}"""

def json_to_human(json_data):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f'Bearer {os.getenv("OPENROUTER")}'
        },
        data=json.dumps({
            "model": "openai/gpt-3.5-turbo", 
            "messages": [
            {
                "role": "user",
                "content": PROMPT.format(json=json_data)
            }
            ]
            
        })
    )
    text = json.loads(response.content.strip())["choices"][0]["message"]["content"]

    return text