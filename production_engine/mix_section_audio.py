import os
import wave
import numpy as np
from scipy.signal import resample

SR = 48000

def load_wav(path, target_sr=SR):
    with wave.open(path, 'rb') as wf:
        orig_sr = wf.getframerate()
        n_frames = wf.getnframes()
        channels = wf.getnchannels()
        raw = wf.readframes(n_frames)
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if channels == 2:
            data = data.reshape(-1, 2).mean(axis=1)
        if orig_sr != target_sr:
            new_len = int(len(data) * target_sr / orig_sr)
            data = resample(data, new_len)
        return data

def mix_section_audio(voiceover_path, sfx_cues, output_audio_path, sfx_dir="production_engine/sfx", target_duration_s=None):
    """
    Mixes voiceover with ducked SFX (-50% volume for subtle elegance) in pristine 48kHz Stereo.
    sfx_cues: list of tuples (time_s, sfx_name, gain)
    """
    vo_audio = load_wav(voiceover_path, SR)
    if target_duration_s is not None:
        req_samples = int(target_duration_s * SR)
        if len(vo_audio) < req_samples:
            vo_audio = np.pad(vo_audio, (0, req_samples - len(vo_audio)), mode='constant')
        elif len(vo_audio) > req_samples:
            vo_audio = vo_audio[:req_samples]
    total_samples = len(vo_audio)
    total_dur = total_samples / SR

    # Peak normalize voiceover to -0.5 dB
    vo_peak = np.max(np.abs(vo_audio))
    if vo_peak > 0:
        vo_audio = vo_audio * (0.94 / vo_peak)

    # Load SFX bank (Halved to 50% volume for subtle, non-distracting background sound)
    SFX_VOLUME_SCALE = 0.50
    sfx_bank = {}
    if os.path.exists(sfx_dir):
        for f in os.listdir(sfx_dir):
            if f.endswith(".wav"):
                key = os.path.splitext(f)[0]
                scale = 0.25 if ("marker" in key or "pencil" in key) else 0.50
                try:
                    sfx_bank[key] = load_wav(os.path.join(sfx_dir, f), SR) * scale
                except Exception:
                    pass

    # Convenience aliases for standard names
    if 'pop_bubble' in sfx_bank: sfx_bank['pop'] = sfx_bank['pop_bubble']
    if 'marker_draw' in sfx_bank: sfx_bank['marker'] = sfx_bank['marker_draw']
    if 'chime_sparkle' in sfx_bank: sfx_bank['chime'] = sfx_bank['chime_sparkle']
    if 'idea_ding' in sfx_bank: sfx_bank['ding'] = sfx_bank['idea_ding']
    if 'mouse_click' in sfx_bank: sfx_bank['click'] = sfx_bank['mouse_click']
    if 'subtle_thud' in sfx_bank: sfx_bank['thud'] = sfx_bank['subtle_thud']

    sfx_track = np.zeros(total_samples, dtype=np.float32)
    for cue in sfx_cues:
        if len(cue) >= 4:
            time_s, sfx_type, gain, max_dur = cue[:4]
        else:
            time_s, sfx_type, gain = cue[:3]
            max_dur = None

        if sfx_type in sfx_bank:
            clip = sfx_bank[sfx_type].copy()

            # Exact-duration trimming: ensures drawing sound stops precisely with the drawing
            if max_dur is not None and max_dur > 0:
                target_len = int(round(max_dur * SR))
                if len(clip) < target_len:
                    repeats = int(np.ceil(target_len / len(clip)))
                    clip = np.tile(clip, repeats)[:target_len]
                else:
                    clip = clip[:target_len].copy()

                # Smooth 40ms fade-out at the end to prevent clicks and sound completely natural
                fade_len = min(int(0.04 * SR), len(clip))
                if fade_len > 0:
                    clip[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)

            idx = int(time_s * SR)
            end = min(total_samples, idx + len(clip))
            dur = end - idx
            if dur > 0:
                sfx_track[idx:end] += clip[:dur] * (gain * SFX_VOLUME_SCALE)


    # Audio Ducking: compress SFX when voiceover is loud
    vo_envelope = np.abs(vo_audio)
    win_len = int(0.12 * SR)
    if win_len > 0:
        kernel = np.ones(win_len, dtype=np.float32) / float(win_len)
        vo_envelope = np.convolve(vo_envelope, kernel, mode='same')

    duck_gain = np.clip(1.0 - (vo_envelope * 0.50), 0.50, 1.0)
    sfx_ducked = sfx_track * duck_gain

    # Spatial Stereo: slight pan for realism
    left_channel = vo_audio * 0.95 + sfx_ducked * 0.90
    right_channel = vo_audio * 0.95 + sfx_ducked * 1.10

    stereo_master = np.vstack([left_channel, right_channel]).T
    peak = np.max(np.abs(stereo_master))
    if peak > 0.96:
        stereo_master = stereo_master * (0.96 / peak)

    stereo_int16 = (stereo_master * 32767.0).astype(np.int16)
    os.makedirs(os.path.dirname(os.path.abspath(output_audio_path)), exist_ok=True)
    with wave.open(output_audio_path, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(stereo_int16.tobytes())

    print(f"Pristine Stereo Audio Master generated: {output_audio_path} ({total_dur:.2f}s)")
    return output_audio_path
