"""
Unit and Integration Tests for AI Audio Dubbing Engine
=====================================================
Covers:
  1. ASR Provider & Segmentation (valid start/end timestamps, SRT formatting)
  2. Translation Layer (segment IDs and timing preservation)
  3. TTS Provider (AudioResult schema)
  4. Duration Matcher (Level 1 passthrough, Level 2 stretch/compress, Level 4 overflow)
  5. Final Audio Mixer (Pause & silence preservation, sample rate, channels, duration)
  6. Pipeline end-to-end flow with metadata validation
"""
from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
import unittest

import numpy as np
import soundfile as sf

from dubbing.models.dubbing_models import (
    SourceSegment,
    TranslatedSegment,
    TranscriptionResult,
    DubbingConfig,
    DurationMatchingConfig,
    DubbingSegment,
)
from dubbing.asr.base import ASRProvider
from dubbing.translation.base import TranslationProvider
from dubbing.tts.base import TTSProvider, AudioResult
from dubbing.timing.duration_matcher import DurationMatcher
from dubbing.audio.processor import AudioProcessor
from dubbing.audio.mixer import Mixer
from dubbing.audio.segmenter import Segmenter
from dubbing.pipeline.dubbing_pipeline import DubbingPipeline


def create_tone_wav(
    filepath: str,
    duration: float,
    freq: float = 440.0,
    sample_rate: int = 48000,
    channels: int = 1,
) -> str:
    """Helper to generate a clean sinusoidal tone WAV file."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    num_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, num_samples, endpoint=False)
    waveform = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    if channels == 2:
        waveform = np.column_stack((waveform, waveform))
    sf.write(filepath, waveform, sample_rate, subtype="PCM_16")
    return filepath


# ── Mocks for testing ─────────────────────────────────────────────────────────

class MockASRProvider(ASRProvider):
    def transcribe(self, audio_path: str, language=None) -> TranscriptionResult:
        segments = [
            SourceSegment(id=0, start=0.0, end=2.0, text="الكيوي أصله الحقيقي من الصين"),
            SourceSegment(id=1, start=2.7, end=5.2, text="وكان اسمه القديم عنب الثعلب الصيني"),
        ]
        return TranscriptionResult(
            segments=segments,
            detected_language="ar",
            language_probability=0.98,
            full_text="الكيوي أصله الحقيقي من الصين وكان اسمه القديم عنب الثعلب الصيني",
        )


class MockTranslationProvider(TranslationProvider):
    def translate(self, text: str, source_language: str, target_language: str) -> str:
        translations = {
            "الكيوي أصله الحقيقي من الصين": "Kiwi actually originated in China.",
            "وكان اسمه القديم عنب الثعلب الصيني": "Its former name was Chinese gooseberry.",
        }
        return translations.get(text, "Translated text.")


class MockTTSProvider(TTSProvider):
    def __init__(self, duration_multiplier: float = 1.0):
        self.multiplier = duration_multiplier

    def synthesize(self, text: str, language: str, voice: str, output_path: str) -> AudioResult:
        # Approximate duration by word count
        dur = max(0.5, len(text.split()) * 0.45 * self.multiplier)
        create_tone_wav(output_path, duration=dur, freq=300.0)
        return AudioResult(audio_path=output_path, duration=dur, sample_rate=48000)


# ── Test Cases ────────────────────────────────────────────────────────────────

class TestDubbingEngine(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="dubbing_test_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # 1. ASR & Segmentation Tests
    def test_asr_and_segmentation(self):
        asr = MockASRProvider()
        result = asr.transcribe("dummy.wav")

        self.assertEqual(result.detected_language, "ar")
        self.assertGreaterEqual(result.language_probability, 0.9)
        self.assertEqual(len(result.segments), 2)

        # Validate segment timings
        for seg in result.segments:
            self.assertGreater(seg.end, seg.start)
            self.assertGreater(seg.duration, 0.0)
            self.assertTrue(len(seg.text) > 0)

        # Validate SRT formatting
        segmenter = Segmenter()
        srt_path = os.path.join(self.test_dir, "test.srt")
        segmenter.save_as_srt(result.segments, srt_path)
        self.assertTrue(os.path.isfile(srt_path))

        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("00:00:00,000 --> 00:00:02,000", content)
        self.assertIn("00:00:02,700 --> 00:00:05,200", content)

    # 2. Translation Tests
    def test_translation_preserves_segment_ids(self):
        asr = MockASRProvider()
        trans = MockTranslationProvider()

        transcription = asr.transcribe("dummy.wav")
        translated_segments = trans.translate_segments(
            segments=transcription.segments,
            source_language=transcription.detected_language,
            target_language="en",
        )

        self.assertEqual(len(translated_segments), 2)
        for orig, tr in zip(transcription.segments, translated_segments):
            self.assertEqual(tr.id, orig.id)
            self.assertEqual(tr.source.start, orig.start)
            self.assertEqual(tr.source.end, orig.end)
            self.assertEqual(tr.language, "en")
            self.assertTrue(len(tr.text) > 0)

    # 3. TTS Provider Test
    def test_tts_synthesis(self):
        tts = MockTTSProvider()
        out_wav = os.path.join(self.test_dir, "tts_out.wav")
        res = tts.synthesize("Hello world", "en", "Kore", out_wav)

        self.assertTrue(os.path.isfile(res.audio_path))
        self.assertGreater(res.duration, 0)
        self.assertEqual(res.sample_rate, 48000)

    # 4. Duration Matching Tests (Specified in User Prompt #20)
    def test_duration_matching_levels(self):
        cfg = DurationMatchingConfig(
            enabled=True,
            max_speed=1.15,
            min_speed=0.90,
            max_duration_error=0.20,
        )
        matcher = DurationMatcher(cfg)

        # Case A: 2.0s target, 2.1s generated -> error = 0.1s <= 0.20s -> Level 1 Passthrough
        src_a = os.path.join(self.test_dir, "case_a_in.wav")
        dst_a = os.path.join(self.test_dir, "case_a_out.wav")
        create_tone_wav(src_a, duration=2.1)
        info_a = matcher.match(src_a, target_duration=2.0, output_path=dst_a)
        self.assertEqual(info_a.strategy, "passthrough")
        self.assertAlmostEqual(info_a.final_duration, 2.1, delta=0.05)

        # Case B: 2.0s target, 2.8s generated -> required speed = 2.8 / 2.0 = 1.40 > 1.15 -> Level 4 Overflow clamped to 1.15
        src_b = os.path.join(self.test_dir, "case_b_in.wav")
        dst_b = os.path.join(self.test_dir, "case_b_out.wav")
        create_tone_wav(src_b, duration=2.8)
        info_b = matcher.match(src_b, target_duration=2.0, output_path=dst_b)
        self.assertEqual(info_b.strategy, "overflow")
        self.assertAlmostEqual(info_b.adjustment_factor, 1.15, delta=0.01)
        expected_dur_b = 2.8 / 1.15
        self.assertAlmostEqual(info_b.final_duration, expected_dur_b, delta=0.1)

        # Case C: 2.0s target, 1.4s generated -> required speed = 1.4 / 2.0 = 0.70 < 0.90 -> Level 4 Overflow clamped to 0.90
        src_c = os.path.join(self.test_dir, "case_c_in.wav")
        dst_c = os.path.join(self.test_dir, "case_c_out.wav")
        create_tone_wav(src_c, duration=1.4)
        info_c = matcher.match(src_c, target_duration=2.0, output_path=dst_c)
        self.assertEqual(info_c.strategy, "overflow")
        self.assertAlmostEqual(info_c.adjustment_factor, 0.90, delta=0.01)
        expected_dur_c = 1.4 / 0.90
        self.assertAlmostEqual(info_c.final_duration, expected_dur_c, delta=0.1)

        # Case D: 2.0s target, 2.22s generated -> error = 0.22s > 0.20s, speed = 2.22/2.0 = 1.11 within [0.90, 1.15] -> Compress
        src_d = os.path.join(self.test_dir, "case_d_in.wav")
        dst_d = os.path.join(self.test_dir, "case_d_out.wav")
        create_tone_wav(src_d, duration=2.22)
        info_d = matcher.match(src_d, target_duration=2.0, output_path=dst_d)
        self.assertEqual(info_d.strategy, "compress")
        self.assertAlmostEqual(info_d.final_duration, 2.0, delta=0.1)

    # 5. Final Audio Mixer Tests (Specified in User Prompt #11 & #20)
    def test_audio_mixer_pause_preservation(self):
        """
        Verify:
          Segment 1: 0.0s -> 2.0s (active audio)
          Silence:   2.0s -> 2.7s (0.7s silence preserved)
          Segment 2: 2.7s -> 5.2s (active audio)
        """
        cfg = DubbingConfig(output_sample_rate=48000, output_channels=2)
        mixer = Mixer(cfg)

        seg1_wav = os.path.join(self.test_dir, "seg1.wav")
        seg2_wav = os.path.join(self.test_dir, "seg2.wav")
        create_tone_wav(seg1_wav, duration=2.0, freq=440.0)
        create_tone_wav(seg2_wav, duration=2.5, freq=880.0)

        seg1 = DubbingSegment(
            id=0,
            source=SourceSegment(id=0, start=0.0, end=2.0, text="one"),
            translated_text="one",
            target_language="en",
            final_audio_path=seg1_wav,
            final_duration=2.0,
        )
        seg2 = DubbingSegment(
            id=1,
            source=SourceSegment(id=1, start=2.7, end=5.2, text="two"),
            translated_text="two",
            target_language="en",
            final_audio_path=seg2_wav,
            final_duration=2.5,
        )

        mixed_wav = os.path.join(self.test_dir, "mixed.wav")
        mixer.mix_segments([seg1, seg2], mixed_wav, total_duration=5.5)

        self.assertTrue(os.path.isfile(mixed_wav))

        # Validate with soundfile
        data, sr = sf.read(mixed_wav)
        self.assertEqual(sr, 48000)
        self.assertEqual(data.ndim, 2)  # Stereo
        self.assertEqual(data.shape[1], 2)

        total_duration = len(data) / sr
        self.assertGreaterEqual(total_duration, 5.2)

        # Check silence between 2.1s and 2.6s (within the 2.0 - 2.7 pause window)
        silence_start_idx = int(2.1 * sr)
        silence_end_idx = int(2.6 * sr)
        silence_slice = data[silence_start_idx:silence_end_idx]
        max_silence_amp = np.max(np.abs(silence_slice))
        self.assertEqual(max_silence_amp, 0.0, "Pause window must be completely silent!")

        # Check active audio in Segment 1 (0.5s to 1.5s)
        seg1_slice = data[int(0.5 * sr) : int(1.5 * sr)]
        self.assertGreater(np.max(np.abs(seg1_slice)), 0.1, "Segment 1 must have active audio!")

        # Check active audio in Segment 2 (3.0s to 4.0s)
        seg2_slice = data[int(3.0 * sr) : int(4.0 * sr)]
        self.assertGreater(np.max(np.abs(seg2_slice)), 0.1, "Segment 2 must have active audio!")

    # 6. End-to-End Pipeline Orchestrator Test
    def test_pipeline_orchestration(self):
        input_audio = os.path.join(self.test_dir, "input.wav")
        create_tone_wav(input_audio, duration=6.0)

        cfg = DubbingConfig(
            asr_model_size="small",
            output_sample_rate=48000,
            output_channels=2,
        )

        pipeline = DubbingPipeline(
            asr_provider=MockASRProvider(),
            translation_provider=MockTranslationProvider(),
            tts_provider=MockTTSProvider(),
            config=cfg,
        )

        progress_log = []

        def on_progress(step: str, progress: float):
            progress_log.append((step, progress))

        result = pipeline.dub(
            audio_path=input_audio,
            target_language="en",
            voice="Kore",
            project_name="test_proj",
            output_base_dir=self.test_dir,
            progress_callback=on_progress,
        )

        # Verify Result object
        self.assertEqual(result.project_id, "test_proj")
        self.assertEqual(result.source_language, "ar")
        self.assertEqual(result.target_language, "en")
        self.assertTrue(os.path.isfile(result.output_audio))
        self.assertTrue(os.path.isfile(result.transcript_path))
        self.assertTrue(os.path.isfile(result.translation_path))
        self.assertTrue(os.path.isfile(result.metadata_path))
        self.assertEqual(len(result.segments), 2)

        # Verify directory structure
        proj_dir = os.path.join(self.test_dir, "test_proj")
        self.assertTrue(os.path.isdir(os.path.join(proj_dir, "source")))
        self.assertTrue(os.path.isdir(os.path.join(proj_dir, "transcription")))
        self.assertTrue(os.path.isdir(os.path.join(proj_dir, "translation")))
        self.assertTrue(os.path.isdir(os.path.join(proj_dir, "segments")))
        self.assertTrue(os.path.isdir(os.path.join(proj_dir, "output")))

        # Verify metadata.json schema
        with open(result.metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.assertEqual(meta["project_id"], "test_proj")
        self.assertEqual(meta["source_language"], "ar")
        self.assertEqual(meta["target_language"], "en")
        self.assertIn("source_audio", meta)
        self.assertIn("dubbed_audio", meta)
        self.assertEqual(len(meta["segments"]), 2)
        self.assertIn("timing", meta["segments"][0])

        # Verify progress callbacks reached 100%
        self.assertGreater(len(progress_log), 5)
        self.assertEqual(progress_log[-1][1], 1.0)


if __name__ == "__main__":
    unittest.main()
