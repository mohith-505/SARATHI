import pytest
from sarathi.core.types import ModelSpec, RouteRequest, TaskType, Privacy, Complexity
from sarathi.models.router import Router, NoModelFits

@pytest.fixture
def router():
    local = [
        ModelSpec(name="qwen3:8b", provider="ollama", weights_vram_mb=4500, kv_bytes_per_token=131072, is_local=True),
        ModelSpec(name="qwen3:4b", provider="ollama", weights_vram_mb=2500, kv_bytes_per_token=131072, is_local=True),
    ]
    cloud = {
        "mid": ModelSpec(name="cloud-mid", provider="openai_compat", is_local=False),
        "reasoning": ModelSpec(name="cloud-reasoning", provider="openai_compat", is_local=False),
        "coding": ModelSpec(name="cloud-coding", provider="openai_compat", is_local=False),
    }
    return Router(local, cloud)

def test_router_secret(router):
    # privacy=SECRET -> local
    req = RouteRequest(privacy=Privacy.SECRET)
    spec = router.route(req, vram_free_mb=6000)
    assert spec.name == "qwen3:8b"

def test_router_offline(router):
    # offline=True -> local
    req = RouteRequest(offline=True)
    spec = router.route(req, vram_free_mb=6000)
    assert spec.name == "qwen3:8b"

def test_router_reason_hard(router):
    req = RouteRequest(task_type=TaskType.REASON, complexity=Complexity.HARD)
    spec = router.route(req)
    assert spec.name == "cloud-reasoning"

def test_router_code(router):
    req = RouteRequest(task_type=TaskType.CODE, complexity=Complexity.NORMAL)
    spec = router.route(req)
    assert spec.name == "cloud-coding"

def test_router_summarize(router):
    # SUMMARIZE -> cheap local if it fits
    req = RouteRequest(task_type=TaskType.SUMMARIZE)
    spec = router.route(req, vram_free_mb=3500)  # Only 4b will fit (2500 + 256 + 500 = 3256)
    assert spec.name == "qwen3:4b"

def test_router_chat_default(router):
    # default plain chat
    req = RouteRequest()
    spec = router.route(req, vram_free_mb=6000)
    assert spec.name == "cloud-mid"

def test_router_secret_oom(router):
    # SECRET with 3 GB free -> raises NoModelFits (correct. Secret must never fall back to cloud)
    req = RouteRequest(privacy=Privacy.SECRET)
    with pytest.raises(NoModelFits):
        router.route(req, vram_free_mb=3000) # Only 4b fits in 3.2G, neither fits in 3G
