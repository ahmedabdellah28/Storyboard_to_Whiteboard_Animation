import os
import time
from dubbing.translation.provider import GeminiTranslationProvider

p = GeminiTranslationProvider()

for m in ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-3.8-flash"]:
    p.model = m
    t0 = time.time()
    try:
        res = p.translate("مرحبا بكم في هذا الفيديو الوثائقي", "ar", "en")
        print(f"Model {m}: SUCCESS in {time.time() - t0:.2f}s -> {res}")
    except Exception as e:
        print(f"Model {m}: FAILED in {time.time() - t0:.2f}s -> {e}")
