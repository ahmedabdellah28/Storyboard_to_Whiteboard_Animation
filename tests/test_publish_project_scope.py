from pathlib import Path

import production_engine.universal_section_pipeline as pipeline_module
from production_engine.universal_section_pipeline import UniversalSectionPipeline


def test_step_publish_uses_pipeline_project_id(tmp_path):
    section = tmp_path / "06_omar_al_mukhtar"
    section.mkdir()
    (section / "final_whiteboard_1080p.mp4").write_bytes(b"video")
    (section / "master_audio.wav").write_bytes(b"audio")

    pipeline = UniversalSectionPipeline(
        section,
        title="عمر المختار",
        project_id="fiercest_warriors_documentary",
    )
    published = Path(pipeline.step_publish())

    expected_dir = (
        PROJECT_ROOT
        / "output_animations"
        / "fiercest_warriors_documentary"
        / "deliverables"
        / "sections"
    )
    assert published.parent == expected_dir
    assert published.read_bytes() == b"video"
    assert (expected_dir / "06_omar_al_mukhtar_Master_Audio.wav").read_bytes() == b"audio"
