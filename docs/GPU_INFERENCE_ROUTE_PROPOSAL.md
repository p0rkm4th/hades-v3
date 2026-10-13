# GPU inference route proposal — approval required

**Status:** adapter code and local fake-upstream security tests are implemented. No network, firewall, Compose routing, host, or inference-service changes have been made. Live candidate traffic is not authorized yet.

## Proposed path

```text
Pydantic / lean / Hermes harness containers
                 |
       internal model-access network
                 |
      fixed-purpose inference proxy
                 |
     egress allowlist for one endpoint
                 |
  existing GPU-backed Ollama service
```

Add a small, fixed-upstream inference adapter to the v3 experiment. Attach it to the existing internal candidate network and to a dedicated egress network. Attach only the candidate API and Hermes containers to the model-access network. Restrict adapter egress at the Docker host to the single approved inference endpoint and service port. It must not accept a caller-supplied upstream, follow redirects, or act as a general HTTP or SOCKS proxy.

Expose only `GET /v1/models` and `POST /v1/chat/completions` to candidate containers; reject every other route and method. For inference, the adapter should translate the common OpenAI-compatible request into Ollama's native `/api/chat` request, fixing the model name and `options.num_ctx=65536`, temperature, and output limit, then translate the non-streaming response back to the common format. Do not expose Ollama administrative endpoints such as model pull, delete, show, or process management to candidates. The adapter may call no other upstream path. Set a small request-body limit, a fixed upstream, finite connection/read timeouts, and a concurrency cap. Keep the existing HADES tool gateway, database, Grocy, workspaces, and commitment simulator off the egress network.

The route needs no SSH tunnel and no SSH key. The Codex break-glass identity remains the read-only discovery path and is never mounted into an experiment container. The proxy has no credential for the inference host; it can forward only the two allowlisted inference API operations to the configured model endpoint.

## Matched inference configuration

For a future authorized comparison, configure Pydantic AI, lean, and Hermes with the same proxy URL, `gemma4:12b` model ID, effective context 65,536, temperature `0`, and 1,024 output-token limit. [Ollama documents that its OpenAI-compatible API has no context-size request field](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx#setting-the-local-context-size), so merely setting a client-side value would not establish a matched effective context. The fixed adapter must set Ollama's native `options.num_ctx` on every inference request. Before each campaign, repeat the model-list, loaded-model context, and GPU-health preflight; confirm `/api/ps` reports 65,536 while the model is loaded. Record a configuration digest and verify that Hermes accepts the context before scoring trials. Use the same prompt, timeout, tool budget, fixture, and candidate order protocol for every harness.

The v3 harness adapters now share temperature and output-token settings. The isolated adapter translates tool calls in both directions and applies the fixed Ollama options on every request. Tests use loopback fake Ollama and redirect-sink servers; no Hypnos request is made. Do not change the existing Ollama service configuration or fabricate context metadata. If the model is evicted or reports a different runtime context, stop the comparison and re-qualify the endpoint.

## Security and experiment implications

- Only synthetic v3 fixture prompts and outputs may cross this route. Keep household, production, and HADES v2 data out of the experiment.
- The adapter becomes the only bridge between the isolated harness and homelab inference. A compromise could issue inference requests and consume GPU resources, but its fixed destination, port, methods, and paths must prevent access to other homelab services.
- Host firewall policy and Docker egress rules are part of the security boundary. Compose network membership alone does not restrict the proxy's outbound destinations.
- The isolated tests prove application-level rejection of caller-supplied destinations, unsupported methods, non-inference routes, model overrides, streaming, and redirects. They do not prove host firewall rules, Docker egress allowlisting, DNS/IP pinning, or isolation from other host networks. Those controls must be implemented and inspected before connecting the adapter to Hypnos.
- Ollama-to-OpenAI tool-call request/response translation and the enforced `num_ctx`, temperature, and output limit are covered against a local fake service. Compatibility with the live Hypnos Ollama version remains unverified until an approved bounded trial.
- Inference traffic to the existing service uses its currently available transport. The proxy does not add authentication or transport encryption to that service; rely on the existing trusted LAN boundary unless the owner requires a separately approved encrypted transport.
- The endpoint is shared infrastructure. A matched run loads a model and consumes GPU memory and compute. Schedule it when that use is acceptable; do not restart, reconfigure, or unload the service.
- The separate network/adapter adds experiment code and configuration that must be reviewed, tested, and removed with the disposable v3 environment. It does not modify HADES v2 or production service routing.

## Approval requested

The design is conditionally approved for preparation. Before live candidate traffic, request explicit authorization for a bounded Hypnos trial covering the fixed upstream endpoint/port, host egress allowlist, permitted API paths, shared GPU workload window, and synthetic-only prompts. Implement and inspect the v3-only network boundary after that authorization, then run all three harnesses on the identical endpoint and configuration.
