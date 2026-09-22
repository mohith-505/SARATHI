# Models and laptop strategy

## Local default

The configured local target is `qwen3:4b` through Ollama. A 4B quantized model is appropriate for the Lenovo LOQ target: roughly 2.5 GB model storage/VRAM plus context and runtime overhead, leaving headroom on a 6 GB GPU. Keep one model loaded and start with an 8k context limit.

For stronger local quality, evaluate a 7B/8B quantized model only after measuring actual VRAM and latency. It may leave too little headroom for long contexts, vision, or other GPU applications. CPU fallback is possible but is expected to be slow.

## Cloud strategy

Cloud models are optional, configured through an OpenAI-compatible endpoint and an environment API key. Use them only when the user explicitly selects cloud/hybrid behavior or a future router's policy allows it. Private, offline, and secret requests must not silently leave the laptop.

## Provider abstraction

`OpenAICompatProvider` accepts OpenAI-compatible chat APIs, which covers Ollama's `/v1` endpoint and compatible cloud gateways. Future dedicated adapters can implement streaming, embeddings, and vision without changing conversation or UI code.
