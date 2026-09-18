import os
import pytest
from pathlib import Path
from sarathi.security.paths import PathPolicy, PolicyDenied

@pytest.fixture
def policy():
    # Provide absolute paths that match the local test environment
    base = Path.cwd().resolve()
    return PathPolicy(
        allow_read=[base / "workspace", base / "projects"],
        allow_write=[base / "workspace"],
        deny_roots=[base / ".ssh"],
        deny_globs=["*.pem", "id_*", ".env", "*/src/sarathi/security/*"]
    )

def test_path_read_inside(policy):
    p = policy.check(Path.cwd() / "workspace/note.txt", "read")
    assert p.name == "note.txt"

def test_path_write_inside(policy):
    p = policy.check(Path.cwd() / "workspace/out.txt", "write")
    assert p.name == "out.txt"

def test_path_read_outside(policy):
    with pytest.raises(PolicyDenied, match="outside allowed roots"):
        policy.check(Path.cwd() / "random/file.txt", "read")

def test_path_traversal(policy):
    # Traversal resolving outside roots
    with pytest.raises(PolicyDenied, match="outside allowed roots"):
        policy.check(Path.cwd() / "workspace/../../etc/passwd", "read")

def test_path_denied_dir(policy):
    with pytest.raises(PolicyDenied, match="inside denied directory"):
        policy.check(Path.cwd() / ".ssh/config", "read")

def test_path_denied_glob_id(policy):
    with pytest.raises(PolicyDenied, match="matches denied pattern"):
        policy.check(Path.cwd() / "workspace/id_rsa", "read")

def test_path_denied_glob_env(policy):
    with pytest.raises(PolicyDenied, match="matches denied pattern"):
        policy.check(Path.cwd() / "workspace/.env", "read")

def test_path_denied_glob_security(policy):
    with pytest.raises(PolicyDenied, match="matches denied pattern"):
        policy.check(Path.cwd() / "workspace/src/sarathi/security/paths.py", "read")

# The symlink escape is a bit harder to test across OS without creating real links,
# but our `_expand` does `.resolve()` which handles it if the OS link exists.
