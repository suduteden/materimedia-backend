from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
import re
from google import genai
import edge_tts

CHARACTERS = {
    "Nain": {"voice": "id-ID-ArdiNeural", "base_pitch": -16, "base_rate": -5},
    "Dzul": {"voice": "id-ID-ArdiNeural", "base_pitch": -4, "base_rate": -2},
    "Rayyan": {"voice": "id-ID-ArdiNeural", "base_pitch": 8, "base_rate": 14},
    "Amar": {"voice": "id-ID-ArdiNeural", "base_pitch": -22, "base_rate": -10},
    "Ramy": {"voice": "id-ID-ArdiNeural", "base_pitch": -2, "base_rate": 3},
    "Mawar": {"voice": "id-ID-GadisNeural", "base_pitch": -4, "base_rate": 0},
    "Khilwa": {"voice": "id-ID-GadisNeural", "base_pitch": 14, "base_rate": 12},
    "Tsurayya": {"voice": "id-ID-GadisNeural", "base_pitch": -8, "base_rate": -6},
    "Putri": {"voice": "id-ID-GadisNeural", "base_pitch": 5, "base_rate": 6},
    "Naina": {"voice": "id-ID-GadisNeural", "base_pitch": -10, "base_rate": -5}
}

EMOTIONS = {
    "Bersemangat": {"volume": "+30%", "pitch_mod": 6, "rate_mod": 10},
    "Profesional": {"volume": "+0%", "pitch_mod": 0, "rate_mod": 0},
    "Ceria": {"volume": "+20%", "pitch_mod": 8, "rate_mod": 8},
    "Sedih": {"volume": "-20%", "pitch_mod": -6, "rate_mod": -20},
    "Marah": {"volume": "+50%", "pitch_mod": -4, "rate_mod": 8},
    "Informatif": {"volume": "+10%", "pitch_mod": 2, "rate_mod": 2},
    "Berbisik": {"volume": "-60%", "pitch_mod": -8, "rate_mod": -15},
    "Tenang": {"volume": "-15%", "pitch_mod": -4, "rate_mod": -10},
    "Dramatis": {"volume": "+15%", "pitch_mod": 4, "rate_mod": -12},
    "Santai": {"volume": "+0%", "pitch_mod": 0, "rate_mod": 4}
}

PHONETIC_DICTIONARY = {
    r'\bADS\b': 'Eds', r'\bAds\b': 'Eds', r'\bads\b': 'eds',
    r'\bAI\b': 'Ei Ai', r'\bAi\b': 'Ei Ai', r'\bai\b': 'ei ai',
    r'\bWhatsApp\b': 'Watsap', r'\bWA\b': 'We A',
    r'\bZoom\b': 'Zum', r'\bMeta\b': 'Meta', r'\bPlus\b': 'Plas'
}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body_raw = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
        try:
            body = json.loads(body_raw)
        except Exception:
            body = {}
        
        text = body.get('text', '')
        character = body.get('character', 'Nain')
        emotion = body.get('emotion', 'Profesional')
        speed_mod = body.get('speed_mod', 0)
        pitch_mod = body.get('pitch_mod', 0)
        volume_mod = body.get('volume_mod', 0)
        gemini_api_key = body.get('gemini_api_key', '')

        char_info = CHARACTERS.get(character, CHARACTERS["Nain"])
        emo_info = EMOTIONS.get(emotion, EMOTIONS["Profesional"])

        naskah_final = text
        active_key = gemini_api_key.strip() or os.environ.get("GEMINI_API_KEY", "")
        if active_key and text:
            try:
                client = genai.Client(api_key=active_key)
                resp = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"Perbaiki naskah gaya {emotion} (tanpa SSML): {text}"
                )
                if resp and resp.text:
                    naskah_final = re.sub(r'<[^>]+>', '', resp.text.strip())
            except Exception:
                pass

        for pat, rep in PHONETIC_DICTIONARY.items():
            naskah_final = re.sub(pat, rep, naskah_final)

        tp = char_info["base_pitch"] + emo_info["pitch_mod"] + pitch_mod
        tr = char_info["base_rate"] + emo_info["rate_mod"] + speed_mod
        tv = int(emo_info["volume"].replace("%", "")) + volume_mod

        out_file = "/tmp/output.mp3"
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _synth():
            comm = edge_tts.Communicate(
                naskah_final, 
                char_info["voice"], 
                rate=f"{tr:+d}%", 
                pitch=f"{tp:+d}Hz", 
                volume=f"{tv:+d}%"
            )
            await comm.save(out_file)
            
        loop.run_until_complete(_synth())

        try:
            with open(out_file, 'rb') as f:
                audio_bytes = f.read()
        except Exception:
            audio_bytes = b''

        self.send_response(200)
        self.send_header('Content-type', 'audio/mpeg')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(audio_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
