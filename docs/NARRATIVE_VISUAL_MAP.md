# Narrative Visual Map Documentation

**Module:** `core/narrative/semantic_beat_binder.py`  
**Purpose:** Deterministic semantic bridge between `VisualManifest` (Contract 1), canonical `script.txt`, and `timing/whisper.json` to generate the canonical `NarrativeVisualMap` (Contract 2: `narrative_visual_map.json`).

---

## 1. Overview & Architecture Rules

The **Semantic Beat Binder** maps script narration to storyboard visual entities without external AI, LLMs, or image embedding models. It adheres strictly to deterministic, reproducible heuristics and the canonical TCM-DS v2 contract system.

```
       VisualManifest (Contract 1)
                  +
           canonical script.txt
                  +
          timing/whisper.json
                  │
                  ▼
      ┌─────────────────────────────┐
      │     SemanticBeatBinder      │
      │  ┌───────────────────────┐  │
      │  │ Step A: Speech Beats  │  │
      │  ├───────────────────────┤  │
      │  │ Step B: Arabic Norm   │  │
      │  ├───────────────────────┤  │
      │  │ Step C: Concepts      │  │
      │  ├───────────────────────┤  │
      │  │ Step D: Entity Binding│  │
      │  ├───────────────────────┤  │
      │  │ Step E: Anchor Resolv │  │
      │  ├───────────────────────┤  │
      │  │ Step F: Continuity    │  │
      │  └───────────────────────┘  │
      └──────────────┬──────────────┘
                     │
                     ▼
       NarrativeVisualMap (Contract 2)
```

### Strict Architectural Boundaries:
- **NO external AI / LLMs:** Concept extraction and anchor matching rely entirely on declarative tables and normalized string matching.
- **NO image analysis / embeddings:** Image semantics are not re-inspected; entity mappings respect the existing `VisualManifest`.
- **NO invented asset IDs:** Only entities confirmed present in `VisualManifest.entities` are bound.
- **Extractor Diagnostics:** Geometry diagnostics (such as `possible_touching_assets`, `much_larger_than_typical_asset`, `possible_composites`) remain diagnostic flags in metadata and are never used to infer semantic identities.
- **Timestamp Purity:** Whisper word and segment boundaries are preserved exactly.

---

## 2. Inputs

The binder requires three primary inputs:

1. **`visual_manifest.json`** (`VisualManifest` model):
   - Output of Task 1 (`AssetSheetAdapter`).
   - Contains catalog of validated `VisualEntity` objects (`visual_id`, `crop_path`, `canonical_bbox`, `diagnostics`).
2. **`script.txt`**:
   - Canonical narrative voiceover script in Arabic.
3. **`timing/whisper.json`**:
   - Word-level and segment-level timestamps extracted by `FasterWhisperEngine`.

---

## 3. Step-by-Step Processing Pipeline

### Step A: Speech Beat Creation
- The canonical script is segmented along sentence punctuation (`.`, `?`, `!`, `؟`) and strong Arabic clause boundaries (`لكن`, `بينما`, `حيث`, `على صوت`, `كل هذ`, `وبس والله`).
- Speech beats are **not** one-per-sentence (a sentence can hold multiple beats) nor one-per-word (words serve as timing cues).
- Each clause is aligned with Whisper word sequences via fuzzy/normalized span matching.
- **Special Case Handling:** Trailing Whisper hallucination/duplications are filtered (`_filter_spurious_whisper_duplicates`) if the canonical script does not contain the repeated phrase.

### Step B: Multi-Tier Arabic Normalization
Arabic text matching reuses `core.sync.arabic_matcher.ArabicMatcher` and follows the strict hierarchy:
1. **Exact:** Direct character-for-character matching.
2. **Normalized:** Strips diacritics (Tashkeel), tatweel (`ـ`), standardizes Alef variants (`أ`, `إ`, `آ` → `ا`), Taa Marbuta (`ة` → `ه`), and Yaa variants (`ى` → `ي`).
3. **Token / Stem:** Tokenized word matching ignoring leading clitics (`و`, `ف`, `ب`, `ك`, `ل`, `ال`).
4. **Phonetic:** Fallback sound-alike distance matching for ambiguous transcriptions.
5. **Contextual:** N-gram contextual span matching within candidate windows.

### Step C: Narrative Concept Generation
- Uses declarative rules defined in `config/semantic_visual_rules.json`.
- Each rule defines:
  - `keyword`: Primary Arabic keyword (e.g. `مخك`, `انتباه`, `وهم`, `حقيقة`).
  - `aliases`: Synonymous phrases and variations.
  - `concept`: Compact visual concept name (e.g. `attention`, `surveillance`, `thinking`, `confusion`, `realization`, `contrast`, `payoff`).
  - `priority`: Weight between `0.0` and `1.0`.
  - `negative_keywords`: Prevention list for false-positive context suppression.
  - `preferred_asset_types`: Desired asset classification hints.

### Step D: Visual Entity Binding
- The binder matches detected narrative concepts against entities present in `VisualManifest`.
- Entities are scored based on semantic affinity and assigned narrative roles:
  - **`hero`**: Dominant focal entity (e.g., character, primary focal icon).
  - **`support`**: Supporting visual reinforcement (e.g., secondary icon, badge).
  - **`context`**: Environmental or conceptual indicator.
  - **`decorative`**: Accent line, flourish, or frame element.
- Each visual binding records `visual_id`, `relevance_score`, `role`, `reason`, and `source_references`.

### Step E: Deterministic Anchor Resolution
- Concepts are resolved against Whisper word timestamps using `DeterministicAnchorResolver`.
- Anchor candidates prioritize:
  1. Primary keywords and aliases found directly within the beat clause (`weight: 1.0 / 0.98`).
  2. Leading 2-word and 3-word n-grams from the beat text (`weight: 0.95 / 0.92`).
  3. Non-stopword significant terms (`weight: 0.85`).
  4. Complete beat text fallback (`weight: 0.75`).
- Guaranteed properties:
  - **Monotonicity:** Anchors strictly progress chronologically; lookahead jumps over intervening beats are prevented.
  - **Bounded:** All timestamps remain inside the total audio duration.
  - **Lead-in:** Standard lead-in offset of 200 ms is preserved for subsequent scheduling stages.

### Step F: Continuity Tracking
- Consecutive beats sharing visual entities flag `continuity: true`.
- Prevents forced exit/re-entry animations when an entity remains relevant across neighboring narrative beats.
- Configures `VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=2.0)`.

---

## 4. Output Contract Validation

The resulting `data/narrative_visual_map.json` validates against `core.contracts.narrative_map.NarrativeVisualMap`:

```json
{
  "contract_type": "narrative_visual_map",
  "version": "2.0",
  "map_id": "map_separated_comic_character_and_icon_asset_sheet",
  "storyboard_hash": "64ca93...",
  "script_hash": "2ff150...",
  "concepts": [
    {
      "concept_id": "cpt_001_brain_illusion_hero",
      "visual_id": "asset_001",
      "narrative_role": "hero",
      "importance_weight": 0.95,
      "anchor_candidates": [
        { "text": "مخك", "weight": 1.0, "type": "identity" },
        { "text": "خدعك مخك", "weight": 0.95, "type": "semantic" }
      ],
      "script_reference_segment": {
        "paragraph_index": 0,
        "full_sentence": "خدعك مخك..."
      },
      "visual_continuity": {
        "persist_after_draw": true,
        "min_hold_after_finish_s": 2.0,
        "allowed_simultaneous_with": []
      },
      "notes": "Bound to asset_001 via rule 'brain_illusion' (score=0.95)"
    }
  ],
  "narrative_flow_rules": [
    {
      "antecedent": "cpt_001_brain_illusion_hero",
      "consequent": "cpt_002_thinking_mind_support",
      "order_constraint": "antecedent_before_consequent",
      "overlap_policy": "SAFE_COMPOSITION"
    }
  ],
  "metadata": {
    "total_speech_beats": 18,
    "total_narrative_concepts": 18,
    "total_visual_bindings": 18,
    "resolved_anchors_count": 18,
    "speech_beats": [...],
    "visual_bindings": [...]
  }
}
```

---

## 5. Verification & Test Suite

The module is verified via `tests/test_semantic_beat_binder.py` covering 12 contract and edge-case tests:
1. `test_valid_manifest_ingestion`: Verifies dictionary, path, and model ingestion.
2. `test_arabic_normalization`: Validates diacritic, alef, and taa-marbuta normalization.
3. `test_exact_anchor_matching`: Confirms direct anchor resolution.
4. `test_normalized_anchor_matching`: Validates matching across variant Arabic spellings.
5. `test_token_fuzzy_matching`: Tests clitic stripping and partial stem matching.
6. `test_repeated_phrase_chronological_advancement`: Guarantees cursor advancement for repeated words.
7. `test_duplicated_whisper_ending_filtering`: Filters trailing duplicate audio transcriptions.
8. `test_missing_word_timestamps_graceful_fallback`: Tests segment and linear interpolation fallbacks.
9. `test_monotonic_timestamps`: Asserts strictly monotonic anchor time order ($T_{i} \le T_{i+1}$).
10. `test_no_asset_ids_invented`: Strictly verifies all bound IDs exist in the manifest.
11. `test_deterministic_output_reproducibility`: Guarantees bit-identical output across repeated runs.
12. `test_pydantic_contract_validation`: Confirms 100% compliance with `NarrativeVisualMap` schema.
