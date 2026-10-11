# Local model profiles

The prototype compares every candidate with the same local endpoint per profile. These are inference configurations, not claims that one model is objectively stronger for every task.

| Profile | Model | Immutable model revision | Quantization | Weight SHA-256 | Context | Runtime |
| --- | --- | --- | --- | --- | ---: | --- |
| Standard | Qwen3-8B | `Qwen/Qwen3-8B-GGUF@7c41481f57cb95916b40956ab2f0b139b296d974` | Q4_K_M | `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` | 8,192 | `llama.cpp` server image `sha256:fc9b506e89c1a1cfdd7bc056480f54dc657c1c04d76839a08642dc280b8ed2f6`, reports `0.6.0-dev (build 11552, commit 23b0202a1)` |
| Stronger | Qwen3-14B | `Qwen/Qwen3-14B-GGUF@530227a7d994db8eca5ab5ced2fb692b614357fd` | Q4_K_M | `500a8806e85ee9c83f3ae08420295592451379b4f8cf2d0f41c15dffeb6b81f0` | 8,192 | Same server image and settings |

Both weights are official Qwen GGUF publications and use the model repositories' Apache-2.0 license. The downloaded local files are ignored by Git. Before using a profile, verify its recorded SHA-256 and start the matching Compose service. Only one model server should run at once to keep CPU load and memory use comparable.

The host has an RTX 3080 Ti Laptop GPU, but this Docker environment does not discover an NVIDIA CDI vendor and has no `nvidia-ctk`; candidate runs therefore use CPU inference. This is a recorded environment limitation, not a conclusion about candidate performance on a GPU. Use the same server build, context length, sampling options, and model weights across candidate harnesses; record all per-trial overrides.

References: [Qwen3-8B-GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF/tree/7c41481f57cb95916b40956ab2f0b139b296d974), [Qwen3-14B-GGUF](https://huggingface.co/Qwen/Qwen3-14B-GGUF/tree/530227a7d994db8eca5ab5ced2fb692b614357fd), [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/server).
