"""Tests for the Markdown document builder."""

# ruff: noqa: S101 - assertions are the preferred testing primitive here

from __future__ import annotations

import importlib
from pathlib import Path
from subprocess import CompletedProcess
from typing import TYPE_CHECKING, NoReturn

import pytest
from x_make_common_x import exporters

from x_make_markdown_x.x_cls_make_markdown_x import XClsMakeMarkdownX

if TYPE_CHECKING:
    from collections.abc import Sequence

    from _pytest.monkeypatch import MonkeyPatch


def test_generate_writes_markdown_and_toc(tmp_path: Path) -> None:
    builder = XClsMakeMarkdownX(wkhtmltopdf_path="")
    builder.add_header("Intro", level=1)
    builder.add_paragraph("Welcome")
    builder.add_header("Details", level=2)
    builder.add_list(["Point A", "Point B"], ordered=True)
    builder.add_toc()

    output_md = tmp_path / "doc.md"
    markdown_text = builder.generate(output_file=str(output_md))

    written = output_md.read_text(encoding="utf-8")
    assert written == markdown_text, "generated markdown should match file contents"
    assert markdown_text.startswith(
        "- [1 Intro]"
    ), "TOC should start with Intro header entry"
    assert (
        "1.1 Details" in markdown_text
    ), "Nested header should appear in generated TOC"
    assert not (
        tmp_path / "doc.pdf"
    ).exists(), "PDF should not be created without wkhtmltopdf"
    assert builder.get_last_export_result() is None


def test_to_html_fallback_when_markdown_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    builder = XClsMakeMarkdownX()

    def fake_import(_name: str, _package: str | None = None) -> NoReturn:
        raise ModuleNotFoundError from None

    monkeypatch.setattr(importlib, "import_module", fake_import)

    result = builder.to_html("<b>bold</b>")

    assert result.startswith("<pre>"), "fallback should wrap output in <pre> tag"
    assert "&lt;b&gt;bold&lt;/b&gt;" in result, "fallback should escape HTML content"


def test_to_pdf_requires_existing_wkhtmltopdf(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    builder = XClsMakeMarkdownX(wkhtmltopdf_path=str(tmp_path / "missing.exe"))

    def _no_binary(**_: object) -> Path | None:
        return None

    monkeypatch.setattr(exporters, "_resolve_binary", _no_binary)

    with pytest.raises(RuntimeError, match="binary not found"):
        builder.to_pdf("<html></html>", str(tmp_path / "out.pdf"))


def test_to_pdf_invokes_shared_exporter(tmp_path: Path) -> None:
    wkhtmltopdf = tmp_path / "wkhtmltopdf.exe"
    wkhtmltopdf.write_text("binary", encoding="utf-8")

    captured: dict[str, Sequence[str]] = {}

    def runner(command: Sequence[str]) -> CompletedProcess[str]:
        captured["command"] = command
        Path(command[-1]).write_text("PDF", encoding="utf-8")
        return CompletedProcess(list(command), 0, stdout="ok", stderr="")

    builder = XClsMakeMarkdownX(
        wkhtmltopdf_path=str(wkhtmltopdf),
        runner=runner,
    )

    out_pdf = tmp_path / "out.pdf"
    builder.to_pdf("<html><body>hi</body></html>", str(out_pdf))

    assert out_pdf.exists(), "PDF output file should be created"
    last_result = builder.get_last_export_result()
    assert last_result is not None
    assert last_result.succeeded is True
    assert captured["command"][-1].endswith("out.pdf")


def test_generate_records_export_result(tmp_path: Path) -> None:
    wkhtmltopdf = tmp_path / "wkhtmltopdf.exe"
    wkhtmltopdf.write_text("binary", encoding="utf-8")

    def runner(command: Sequence[str]) -> CompletedProcess[str]:
        Path(command[-1]).write_text("PDF", encoding="utf-8")
        return CompletedProcess(list(command), 0, stdout="ok", stderr="")

    builder = XClsMakeMarkdownX(
        wkhtmltopdf_path=str(wkhtmltopdf),
        runner=runner,
    )
    builder.add_header("Intro")

    output_md = tmp_path / "doc.md"
    builder.generate(output_file=str(output_md))

    result = builder.get_last_export_result()
    assert result is not None
    assert result.succeeded is True
    assert result.output_path == tmp_path / "doc.pdf"
