# Local model profiles

The prototype compares every candidate with the same local endpoint per profile. These are inference configurations, not claims that one model is objectively stronger for every task.

| Profile | Model | Immutable model revision | Quantization | Weight SHA-256 | Context | Runtime |
| --- | --- | --- | --- | --- | ---: | --- |
| Standard | Qwen3-8B | `Qwen/Qwen3-8B-GGUF@7c41481f57cb95916b40956ab2f0b139b296d974` | Q4_K_M | `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` | 40,960 | `llama.cpp` server image `sha256:fc9b506e89c1a1cfdd7bc056480f54dc657c1c04d76839a08642dc280b8ed2f6`, reports `0.6.0-dev (build 11552, commit 23b0202a1)` |
| Stronger | Qwen3-14B | `Qwen/Qwen3-14B-GGUF@530227a7d994db8eca5ab5ced2fb692b614357fd` | Q4_K_M | `500a8806e85ee9c83f3ae08420295592451379b4f8cf2d0f41c15dffeb6b81f0` | `n_ctx=40,960`, `n_ctx_train=40,960` (verified from `/v1/models`) | Same server image and settings |

Both weights are official Qwen GGUF publications and use the model repositories' Apache-2.0 license. The downloaded local files are ignored by Git. Before using a profile, verify its recorded SHA-256 and start the matching Compose service. Only one model server should run at once to keep CPU load and memory use comparable. Qwen3-8B and Qwen3-14B both report `n_ctx=40,960` and `n_ctx_train=40,960`; llama.cpp caps a 65,536 request at that limit. The Compose configuration now requests 40,960 to avoid that cap warning. The prepared stronger profile therefore does not satisfy Hermes's 64,000-token minimum.

The laptop's RTX 3080 Ti is healthy locally, but this Docker environment does not discover an NVIDIA CDI vendor and has no `nvidia-ctk`; candidate runs therefore use CPU inference. This is a recorded environment limitation, not a conclusion about candidate performance on a GPU.

## Discovered homelab GPU profile

Read-only discovery on 2026-10-11 found a reachable Ollama-compatible endpoint with Qwen3.6 35B Q4_K_M available. Its loaded-model record reported an effective `context_length=65,536`, which meets Hermes Agent's verified 64,000-token floor. The `/api/ps` value is the observed serving context; the model's training-context limit was not established from this endpoint, so it is not claimed here. Other Qwen3 8B/14B entries on that endpoint report 40,960 in the model catalog.

The endpoint's four Quadro P4000 devices reported a healthy NVIDIA 580.178.04 driver through `nvidia-smi`. During a bounded generation, 250 ms samples showed GPU utilization rise from idle to peaks of 24%, 19%, 24%, and 40% across the four devices; the Ollama `llama-server` process held roughly 5.8–7.7 GiB on each. Four short native Ollama completions generated 24–95 tokens at 27.65–37.60 tokens/s (median 32.86). These are operational probes, not a benchmark or candidate comparison; prompt lengths and completion lengths were deliberately small. No service restart, configuration change, model download, or driver change was made.

Two other homelab Ollama/OpenAI-compatible catalogs were reachable. One listed Gemma 4 12B with catalog context metadata 262,144 but had no loaded model, so its effective serving context and GPU generation were not verified. The other listed Qwen3 8B without context metadata; its effective context was not available. The laptop has a healthy RTX 3080 Ti driver but no local Ollama listener on port 11434.

This 65,536-context profile meets Hermes's context threshold, but it is not yet usable by the comparison containers: their Compose operator network is intentionally `internal: true`, and the remote homelab endpoint is outside that network. I did not widen the network or add a proxy. Until an isolated, reviewed route is available, all A/C candidate comparisons remain on the same local Qwen3-8B CPU profile. The four direct GPU calls were discovery probes, not matched A/B/C trials.

Hermes Agent enforces a 64,000-token minimum context. Its API server rejected the prepared 40,960-token Qwen3-8B profile before model/tool execution. Never override context metadata to claim 64K. The discovered profile meets the numeric floor, but a future Hermes comparison still needs a common, reachable endpoint and a measured effective context of at least 64,000 tokens.

References: [Qwen3-8B-GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF/tree/7c41481f57cb95916b40956ab2f0b139b296d974), [Qwen3-14B-GGUF](https://huggingface.co/Qwen/Qwen3-14B-GGUF/tree/530227a7d994db8eca5ab5ced2fb692b614357fd), [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/server).
