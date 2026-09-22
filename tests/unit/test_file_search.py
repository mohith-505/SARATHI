import pytest

from sarathi.core.types import Context
from sarathi.security.paths import PathPolicy
from sarathi.tools.impl.fs import SearchFilesTool


@pytest.mark.asyncio
async def test_search_finds_folder_names_and_skips_dependency_trees(tmp_path):
    (tmp_path / "starter").mkdir()
    (tmp_path / "starter-v02").mkdir()
    (tmp_path / "notes.txt").write_text("Starter comparison", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.txt").write_text("starter", encoding="utf-8")

    policy = PathPolicy([tmp_path], [tmp_path / "workspace"], [], [])
    tool = SearchFilesTool(policy)
    result = await tool.run(tool.schema(query="starter", path=str(tmp_path)), Context(session_id="test"))

    assert "[d] starter" in result
    assert "[d] starter-v02" in result
    assert "notes.txt:1" in result
    assert "ignored.txt" not in result
