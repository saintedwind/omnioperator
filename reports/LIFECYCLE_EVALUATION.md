# Lifecycle-constrained local-model evaluation

## What changed

The environment now exposes only tools available in its current lifecycle. A completed inspection cannot be repeated, and export is exposed only after inspection with write capability. Finish and refuse remain explicit model decisions; premature completion still fails independent verification. There is no scripted choice of the next action and no automatic completion.

The adapter sends the available-tool enum to the local server and independently rejects out-of-state responses. These are environment constraints, not evidence the model learned a workflow. Tool errors remain visible to the model with a bounded retry budget.

Outcome verification rechecks the original checksum and independently recomputes statistics for both inspection and export. Changed sources, corrupt/missing output, and modified in-memory reports cannot count as success. Usage and response traces are now scoped to each episode when an adapter is reused.

## Real run

The unchanged six declared English/Persian development cases ran against the actual UCI CSV and the existing local Qwen3-0.6B Q8_0 model. Success increased from 0/6 to 2/6. These are reused development cases, not a held-out benchmark. The improvement belongs to the combined constrained system, not a new model or training run. All previous failure traces remain available.

| Case | Outcome | Model calls |
|---|---|---:|
| export | recovery_budget | 4 |
| inspect | verified | 2 |
| paraphrase | recovery_budget | 4 |
| persian_export | recovery_budget | 4 |
| persian_inspect | verified | 2 |
| unsupported | recovery_budget | 3 |

Both inspection-only requests completed. All three export requests and the unsupported request failed. The model still cannot reliably plan a report export or refuse unsupported work. Unsupported operations are absent from the executor; a failed refusal is not a demonstrated unsafe shell execution.

The raw record is `direct-live-lifecycle.json`; numerical comparison is `lifecycle-comparison.json`. Source SHA-256: `13277ae5d8581e80b7be09d47c7d3d06fe9b8e957078f2cf6e859f955e62f996`. No paid inference was used; the owned loopback model server was stopped after execution. The dataset is historical real data, not a live sensor feed.

## Verification and remaining work

68 local tests passed, including changed-source verification, missing/corrupt report handling, lifecycle constraints, bounded repetition, recovery from an export-before-inspection error, and per-episode usage. Scripted regression probes verify code behavior and are not model performance evidence.

Next, compare a stronger instruction model using the same cases and record its checksum and runtime. Only after freezing that configuration should new independent tasks be scored. Export/refusal reliability and true desktop interaction remain unresolved. Source and recorded results are included in this repository.
