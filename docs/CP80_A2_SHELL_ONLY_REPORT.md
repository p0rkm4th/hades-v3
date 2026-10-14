# CP80 — A2 Shell-only workspace composition

**Evidence class:** CONTRACT TEST
**Candidate:** separate A2 Pydantic AI Harness proof; historical Candidate A unchanged
**Runtime pins:** `pydantic-ai-harness==0.56.0`, `pydantic-ai-slim==2.56.0`; pinned transitive lock in the A2 spike
**Model:** deterministic Pydantic `FunctionModel`, not a live or scored model

## Hypothesis

The upstream Harness `FileSystem` capability may add avoidable command/effect overhead when HADES already provides a task-bound shell workspace. A Shell-only profile should be retained if it can read the actual source, make the intended conditional edit, run tests, and pass the same independent postcondition with fewer gateway effects.

## Matched method

Both profiles used the same synthetic discount task wording, initial repository fixture, task/user/domain identity, gateway-backed command-only `WorkspaceBackend`, 20-second command limit, deterministic model behavior, and independent oracle. Profile order alternated. The only treatment was whether the Harness exposed `FileSystem` alongside `Shell` or exposed `Shell` alone. Each run began after resetting only the disposable amber workspace fixture. Every candidate command went through authenticated `workspace_exec`; an independent gateway command reran tests and checked canonical source plus task/effect state.

The deterministic peer read the source observation returned by its actual tool call before generating a hash-conditional replacement. Shell-only used three ordinary shell operations: read/hash source, compare-and-write against that hash, and run tests. The task remained `RUNNING` intentionally; task finalization is outside this Harness composition test.

## Results

| Profile | Repetitions | Candidate model calls | Candidate tool calls | Candidate gateway effects/run | Oracle effects/run | Confirmed state and independent oracle |
|---|---:|---:|---|---:|---:|---|
| Shell + FileSystem | 4 | 4 each | `read_file`, `write_file`, `run_command` | 18 | 1 | All confirmed; source and tests pass; accurate final text |
| Shell only | 4 | 4 each | `run_command` ×3 | 3 | 1 | All confirmed; source and tests pass; accurate final text |

Independent PostgreSQL inspection found four `RUNNING` tasks per profile, all bound to the amber fixture identity. Shell + FileSystem tasks had 19 total confirmed workspace effects (18 candidate plus one oracle); Shell-only tasks had 4 (three candidate plus one oracle). Effect IDs were unique. No memory or non-workspace effect was recorded. Task IDs and per-run outcomes are preserved in [`cp80_a2_workspace_profiles.jsonl`](../experiment/results/cp80_a2_workspace_profiles.jsonl).

## Interpretation

For this bounded repository change, Shell-only preserved the observed tool result, exact conditional update, test result, answer, and independent final-state check while reducing candidate gateway effects from 18 to 3 per run (15 fewer, 83.3%). Both used four deterministic model turns. This is meaningful composition evidence in favor of omitting the extra `FileSystem` capability for a task that can be completed naturally through the authenticated shell workspace.

This does **not** establish live-model behavior, general repository-agent quality, shell isolation beyond the existing fixture boundary, task completion, recovery from uncertain shell commands, or owner usability. It does not rescore Candidate A and does not justify removing general computer agency. The next test should use a held-out repository task with a real candidate model only if a separate approved model campaign is available; no Hypnos inference is authorized here. Continue using the gateway-backed workspace, not `LocalWorkspaceBackend` or direct host shell.

## Reproducibility and cleanup

The exact A2 package lock and gateway adapter are under `experiment/spikes/a2_gateway_workspace/`. CI repeats three matched pairs with disposable workspace reset between runs and removes only its unique Compose project. Local CP80 used a uniquely named isolated Compose project; the fixture stack is left available for the designated cleanup lead to review. Tern performed no artifact deletion. No shared project, HADES v2 service, production infrastructure, GPU route, or firewall was changed.
