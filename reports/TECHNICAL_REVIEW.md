# Technical review â€” 2026-10-17

## Findings fixed

1. **Policy bypass in dispatch:** controller used the original proposal, ignoring truncated/normalized parameters. Dispatch now uses `decision.params`; regression tests inspect backend state.
2. **False completion:** adapter `done` implied success without evidence. A separate verifier now checks the goal; absent/failed verification cannot report success.
3. **False sandbox claim:** regex path replacement failed for traversal, command substitution, interpreters and Windows paths. Removed rewriting; shell is disabled by default, including when confirmed.
4. **Ignored confirmation configuration:** controller and policy action requirements are now enforced. Episode-wide approval is rejected.
5. **Execution failures hidden:** backend errors stop the episode instead of allowing a subsequent `done` to overwrite failure.
6. **Untrusted model types:** string `false` could become true. Parser rejects non-boolean completion and invalid action/parameter shapes. Malformed adapter proposals stop safely.
7. **Token accounting:** episodes use deltas rather than adapter lifetime totals. Script estimates remain estimates.
8. **No runnable environment:** added a dependency-free demo with observable state and independent completion oracle.
9. **Benchmark factory errors:** now recorded per task; nonempty approval flags are rejected.
10. **Inconsistent observations:** observation text derives from the captured framebuffer instead of a second framebuffer read.

## Theoretical assessment

This is a proposal/execution loop with a scripted policy adapter, not evidence of learned planning or multimodal grounding. Exact framebuffer string search does not measure visual generalization. A stop signal is a claim; outcome verification must be independent. Policy checks reduce some mistakes but cannot enforce OS isolation. Budget checks are cooperative rather than preemptive.

## Remaining work before a real desktop release

- A real isolated backend with explicit capabilities and per-action approval handling.
- Trusted target identification and freshness checks; text labels from a model are insufficient.
- Actual image-input adapter and separately consented model evaluation; none was run here.
- Hard call timeouts, bounded/redacted durable logs, recovery semantics and adversarial task suite.
- Independent user-authored tasks and measured completion across layout variations.

## Validation boundary

Unit/regression suite and local simulated integration run only. No host desktop actions, paid model calls, customer data, or deployment were used. See acceptance.json for raw observed final state. Tests cover concrete regressions, not proof of general safety.

## Real-data extension — 2026-10-17

The real-file backend now executes a fixed inspect/export plan on the original UCI Air Quality CSV (SHA in data/manifest.json). All 13 numeric column means and missing counts were cross-checked using a separate pandas implementation. The loopback report viewer was read in a real browser; its rendered output is in live-review.png. Four HTTP checks and 43 unit/regression tests passed.

This is actual file processing and a live local HTTP viewer, not live model inference or desktop automation. Dataset download initially encountered DNS delays; one verified source archive completed. Raw data is excluded from publication because of conflicting source usage notices. The initial pytest temporary-directory failure was environmental and resolved by selecting a writable workspace temp directory; the final suite passed. Wheel build unavailable locally (pip/setuptools absent).
