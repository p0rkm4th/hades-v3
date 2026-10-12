# Public history remediation

On 2026-10-12, with owner approval, the HADES v3 public `main` history was rewritten to remove private network address literals from five historical blob versions in `docs/COMPARISON_REPORT.md` and `docs/CURRENT_STATE.md`. The affected literals were replaced with `[private address redacted]`. All 102 commits, including the previously unpublished CP62 and full-history audit commits, were retained in order. Tree-by-tree verification confirmed that no other tracked content changed during the rewrite.

The rewritten history was audited for private network details, credentials, personal information, and unintended content changes before publication. A permission-restricted recovery bundle and the original-to-rewritten commit map are retained outside this public repository.

GitHub caches, forks, mirrors, search indexes, and existing clones may retain the superseded commit objects or copies of the old documentation. The rewrite cannot guarantee removal from those external copies. The affected values are not repeated here. Anyone with a clone should replace it with a fresh clone of the current public `main` and remove their old copy if they need the sanitized history.

Before publication, the isolated Compose experiment suite passed (three tests passed; two commitment tests were skipped because they require an operator-issued grant). The clean disposable-fixture smoke check passed.
