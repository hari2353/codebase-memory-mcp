from pathlib import Path
from unittest.mock import patch, MagicMock
from codebase_memory_mcp.convert import convert, pdf_to_text, UnsupportedFormat


def test_convert_plain_text(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello")
    assert convert(p) == "hello"


def test_convert_unsupported_raises(tmp_path):
    p = tmp_path / "a.xyz"
    p.write_text("x")
    try:
        convert(p)
        assert False, "expected UnsupportedFormat"
    except UnsupportedFormat:
        pass


def test_pdf_to_text_calls_mineru(tmp_path, monkeypatch):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    fake = MagicMock(returncode=0, stdout="# Title\n", stderr="")
    with patch("codebase_memory_mcp.convert.subprocess.run", return_value=fake) as m:
        out = pdf_to_text(pdf)
    assert out == "# Title\n"
    m.assert_called_once()
    assert "parse" in m.call_args.args[0]

