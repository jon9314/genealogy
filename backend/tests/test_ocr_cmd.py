from pathlib import Path

from app.core.ocr_runner import build_ocr_cmd
from app.core.settings import Settings


def _dummy_paths(tmp_path: Path) -> tuple[Path, Path]:
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"
    return input_pdf, output_pdf


def test_build_ocr_cmd_defaults(tmp_path):
    settings = Settings()
    input_pdf, output_pdf = _dummy_paths(tmp_path)

    cmd = build_ocr_cmd(input_pdf, output_pdf, settings)

    assert cmd[0] == settings.ocrmypdf_executable
    assert cmd[-2:] == [str(input_pdf), str(output_pdf)]
    assert "--fast-web-view" in cmd
    flag_index = cmd.index("--fast-web-view")
    assert cmd[flag_index + 1] == str(settings.fast_web_view_mb)


def test_build_ocr_cmd_without_fast_web_view(tmp_path):
    settings = Settings(fast_web_view_mb=0)
    input_pdf, output_pdf = _dummy_paths(tmp_path)

    cmd = build_ocr_cmd(input_pdf, output_pdf, settings)

    assert "--fast-web-view" not in cmd


def test_build_ocr_cmd_with_background_removal(tmp_path):
    settings = Settings(remove_background=True)
    input_pdf, output_pdf = _dummy_paths(tmp_path)

    cmd = build_ocr_cmd(input_pdf, output_pdf, settings)

    assert "--remove-background" in cmd
