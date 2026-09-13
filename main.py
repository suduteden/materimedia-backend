from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import edge_tts
import asyncio
import os
import re

app = FastAPI(title="Materimedia Voice Over API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class GenerationRequest(BaseModel):
    text: str
    character: str = "Nain"
    emotion: str = "Profesional"
    speed_mod: int = 0
    pitch_mod: int = 0
    volume_mod: int = 0
    gemini_api_key: str = ""

@app.post("/api/generate")
async def generate_voice(req: GenerationRequest):
    char_info = CHARACTERS.get(req.character, CHARACTERS["Nain"])
    emo_info = EMOTIONS.get(req.emotion, EMOTIONS["Profesional"])
    
    naskah_final = req.text
    active_key = req.gemini_api_key.strip() or os.environ.get("GEMINI_API_KEY", "")
    if active_key:
        try:
            client = genai.Client(api_key=active_key)
            resp = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Perbaiki naskah gaya {req.emotion} (tanpa SSML): {req.text}"
            )
            naskah_final = re.sub(r'<[^>]+>', '', resp.text.strip())
        except Exception:
            pass

    for pat, rep in PHONETIC_DICTIONARY.items():
        naskah_final = re.sub(pat, rep, naskah_final)

    tp = char_info["base_pitch"] + emo_info["pitch_mod"] + req.pitch_mod
    tr = char_info["base_rate"] + emo_info["rate_mod"] + req.speed_mod
    tv = int(emo_info["volume"].replace("%", "")) + req.volume_mod

    out_file = "output.mp3"
    comm = edge_tts.Communicate(
        naskah_final, 
        char_info["voice"], 
        rate=f"{tr:+d}%", 
        pitch=f"{tp:+d}Hz", 
        volume=f"{tv:+d}%"
    )
    await comm.save(out_file)
    return FileResponse(out_file, media_type="audio/mpeg", filename="materimedia-vo.mp3")
