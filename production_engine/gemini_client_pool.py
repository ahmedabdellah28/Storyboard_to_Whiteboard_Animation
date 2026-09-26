import os
import sys
import time
import re
from google import genai
from google.genai import types
from google.genai.errors import ClientError

ROOT_DIR = r"E:\image_to_animate"

def load_all_api_keys():
    keys = []
    env_path = os.path.join(ROOT_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY"):
                    parts = line.split("=", 1)
                    if len(parts) == 2 and parts[1].strip():
                        keys.append(parts[1].strip())
    if not keys and os.environ.get("GEMINI_API_KEY"):
        keys.append(os.environ["GEMINI_API_KEY"])
    return keys

class GeminiClientPool:
    def __init__(self):
        self.keys = load_all_api_keys()
        if not self.keys:
            raise ValueError("No GEMINI_API_KEY found in .env!")
        self.clients = [genai.Client(api_key=k) for k in self.keys]
        self.current_idx = 0
        self._consecutive_429 = 0  # Track consecutive 429s across all keys
        print(f"🔑 GeminiClientPool initialized with {len(self.clients)} API keys.", flush=True)

    def get_current_client(self):
        return self.clients[self.current_idx]

    def rotate_key(self):
        prev = self.current_idx
        self.current_idx = (self.current_idx + 1) % len(self.clients)
        print(f"  🔄 Rotating API Key: from key #{prev+1} -> key #{self.current_idx+1}", flush=True)

    def _handle_429(self, err_str):
        """Handle rate limit: rotate keys, and if all keys exhausted do a full cooldown."""
        self._consecutive_429 += 1
        print(f"  ⚠️ Key #{self.current_idx+1} hit rate limit (429).", flush=True)

        if self._consecutive_429 >= len(self.clients):
            # All keys exhausted — extract delay or use default 50s cooldown
            delay_match = re.search(r'retryDelay[\'"]?:\s*[\'"]?([0-9]+)s', err_str)
            delay = int(delay_match.group(1)) + 5 if delay_match else 50
            delay = max(delay, 50)
            print(f"  🔴 All {len(self.clients)} keys exhausted! Cooling down {delay}s to reset RPM quota...", flush=True)
            time.sleep(delay)
            self._consecutive_429 = 0
        
        self.rotate_key()
        time.sleep(2.0)

    def execute_stream_with_retry(self, model, contents, config, max_retries=100):
        attempts = 0
        cur_model = model
        while attempts < max_retries:
            attempts += 1
            client = self.get_current_client()
            try:
                audio_data = bytearray()
                stream = client.models.generate_content_stream(model=cur_model, contents=contents, config=config)
                for chunk in stream:
                    if chunk.parts:
                        for p in chunk.parts:
                            if p.inline_data and p.inline_data.data:
                                audio_data.extend(p.inline_data.data)
                self._consecutive_429 = 0  # Reset on success
                return bytes(audio_data)
            except ClientError as e:
                err_str = str(e)
                if "limit: 10" in err_str or "GenerateRequestsPerDay" in err_str:
                    alt_model = "gemini-3.1-flash-tts-preview" if cur_model == "gemini-2.5-flash-preview-tts" else "gemini-2.5-flash-preview-tts"
                    if getattr(self, '_last_switched_key', None) != self.current_idx:
                        self._last_switched_key = self.current_idx
                        print(f"  🔄 Key #{self.current_idx+1} {cur_model} daily limit reached. Trying {alt_model}...", flush=True)
                        cur_model = alt_model
                        time.sleep(1.0)
                        continue
                    else:
                        print(f"  ⚠️ Key #{self.current_idx+1} exhausted for both TTS models. Rotating key...", flush=True)
                        self._last_switched_key = None
                        self._handle_429(err_str)
                        continue
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    self._last_switched_key = None
                    self._handle_429(err_str)
                    continue
                else:
                    raise e
            except Exception as e:
                print(f"  ⚠️ Non-client error: {e}, retrying in 5s...", flush=True)
                time.sleep(5)
        raise RuntimeError(f"Failed to execute stream on model {cur_model} after {max_retries} attempts.")

    def execute_content_with_retry(self, model, contents, config=None, max_retries=60):
        attempts = 0
        cur_model = model
        while attempts < max_retries:
            attempts += 1
            client = self.get_current_client()
            try:
                resp = client.models.generate_content(model=cur_model, contents=contents, config=config)
                self._consecutive_429 = 0  # Reset on success
                return resp
            except ClientError as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    self._handle_429(err_str)
                    continue
                else:
                    raise e
            except Exception as e:
                err_s = str(e)
                if ("503" in err_s or "UNAVAILABLE" in err_s) and cur_model != "gemini-3.5-flash":
                    print(f"  🔄 503 spike on {cur_model}. Switching to gemini-3.5-flash...", flush=True)
                    cur_model = "gemini-3.5-flash"
                    time.sleep(2)
                    continue
                print(f"  ⚠️ Non-client error: {e}, retrying in 5s...", flush=True)
                time.sleep(5)
        raise RuntimeError(f"Failed to execute content on model {cur_model} after {max_retries} attempts.")

_global_pool = None

def get_client_pool():
    global _global_pool
    if _global_pool is None:
        _global_pool = GeminiClientPool()
    return _global_pool
