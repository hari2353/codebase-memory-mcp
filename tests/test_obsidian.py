import tempfile
from pathlib import Path
from codebase_memory_mcp.obsidian import scan_vault, ingest_vault, parse_note
from codebase_memory_mcp.memorygraph import MemoryGraph


def _make_vault(tmp_path):
    v = tmp_path / "vault"
    v.mkdir()
    (v / "note1.md").write_text("# Hello\nBody text #tag1\nLinks to [[note2]]\n")
    (v / "note2.md").write_text("Second note #tag2\n")
    (v / ".obsidian").mkdir()
    (v / ".obsidian" / "app.json").write_text("{}")
    return v


def test_scan_vault_skips_obsidian_dir():
    with tempfile.TemporaryDirectory() as d:
        v = _make_vault(Path(d))
        notes = scan_vault(v)
        assert len(notes) == 2
        assert all(".obsidian" not in n["path"] for n in notes)


def test_parse_note_extracts_links_and_tags():
    with tempfile.TemporaryDirectory() as d:
        v = _make_vault(Path(d))
        n = parse_note(v / "note1.md", v)
        assert n["title"] == "note1"
        assert "note2" in n["links"]
        assert "tag1" in n["tags"]


def test_ingest_vault_projects_into_memory_graph():
    with tempfile.TemporaryDirectory() as d:
        v = _make_vault(Path(d))
        g = MemoryGraph()
        n = ingest_vault(v, g)
        assert n == 2
        assert g.get_entity("note:note1") is not None
        assert g.get_entity("tag:tag1") is not None
        ctx = g.context_for("note:note1")
        assert ctx is not None and len(ctx["episodes"]) == 1
        g.close()

