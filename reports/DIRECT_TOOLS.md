# Direct-tool experiment: 2026-10-17

The local candidate exposes inspect_dataset and export_report as direct operations. Calls have a strict JSON schema with no model-selected paths or extra arguments. Completion and refusal are separate choices. The executor checks prerequisites, validates the input checksum, refuses ungranted writes and preserves existing report files. Independent verification checks the resulting file; the model cannot approve its own output.

A run stops after repeated successful calls that leave state unchanged. Failed tools and premature completion receive explicit error feedback, with a bounded recovery budget. There is no scripted fallback that chooses a tool on the model's behalf.

## Actual result

62 unit/regression tests passed locally on Python 3.12.14. These tests include simulated decision sequences and do not measure model intelligence.

Real Qwen3-0.6B Q8_0 inference was run over six declared English/Persian development probes on the original UCI sensor CSV. Initial direct-tool iteration: 0/6 completed. The model inspected the file but repeated operations or failed to finish/refuse correctly. After adding no-progress detection, the same six cases still completed 0/6. The five supported tasks stopped after 3 calls each rather than 7; the unsupported task stopped after 5 calls rather than 6. Raw responses, usage and traces are retained in direct-live-initial.json and direct-live.json. Numeric totals are in direct-comparison.json.

On the original three English requests, the old keyboard-style interface and the new direct interface both scored 0/3 completed episodes. A successful inspection within a failed episode is not presented as task success. The new interface and stopping rules improve execution clarity and resource limits; reliable model planning is unresolved.

These are development probes, not an independent holdout. The test harness supplied write capability separately for export tasks; this is not proof the model understands user authorization. Unsupported requests were not correctly refused, although no shell/deletion capability exists. No model weights were updated, no paid API was used, and the owned model runtime was stopped after the run.

## Reproduce

From the source root, obtain the data using the documented source workflow, start an OpenAI-compatible local model server on 127.0.0.1:8081, and run:

```sh
python -m scripts.direct_live
python -m pytest
```

The candidate remains local. Published baseline remains commit 83013c3f18326677aef914b8cf24e4f78f23e1e9. Next useful comparison is a stronger local instruction model on the frozen cases, followed by additional independently authored tasks. Prompt changes should retain the failed traces and avoid replacing them with selected successful examples.
