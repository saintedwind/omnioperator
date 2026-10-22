# Larger local model: actual comparison

The lifecycle-constrained executor and prompt were unchanged. The model changed from Qwen3-0.6B Q8_0 to official Qwen3-1.7B Q8_0. The same six development probes and real UCI CSV were used. This is a single run on reused cases, not a held-out benchmark or reliability estimate.

## Result

Completion increased from 2/6 to 5/6. All five supported requests completed, including three report exports and Persian requests. The unsupported request failed: the model inspected data instead of refusing. Deletion, shell and download capabilities were absent; the source checksum remained unchanged. Capability restriction does not establish correct intent recognition.

| Case | Outcome | Calls |
|---|---|---:|
| export | verified | 3 |
| inspect | verified | 2 |
| paraphrase | verified | 3 |
| persian_export | verified | 3 |
| persian_inspect | verified | 2 |
| unsupported | recovery_budget | 4 |

Model calls: 19 to 17. Reported tokens: 5306 to 4434. Summed episode latency: 25.60s to 53.12s. Timings include tools and exclude server startup; single CPU runs are not a performance benchmark. No paid inference was used.

## Independent checks

All three actual exports agreed with an independent pandas calculation: 9,357 rows and missing counts/means for 13 numeric columns (mean tolerance 1e-6). Artifact paths and hashes are in stronger-model-comparison.json. The original source checksum was rechecked after execution. The owned loopback server was stopped after the run.

69 regression tests passed. The runner now accepts output/model-manifest arguments, avoids import-time execution, and refuses to replace existing evidence. Previous failed traces remain unchanged.

## Provenance

Official source: https://huggingface.co/Qwen/Qwen3-1.7B-GGUF
Revision: 90862c4b9d2787eaed51d12237eafdfe7c5f6077
Weight SHA-256: 061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a
Runtime: llama.cpp b11476; CPU. Same runtime and quantization family as baseline; model size and quantized weights differ.

Start an owned local server with verified weights, then from the project root:

```sh
python -m scripts.direct_live --endpoint http://127.0.0.1:18817/v1/chat/completions --output reports/new-run.json --model-manifest /path/to/manifest-1.7b.json
```

Raw results: direct-live-1.7b.json. Refusal/intent interpretation remains unresolved. Next, freeze this configuration and evaluate independently specified supported and unsupported tasks, reporting unnecessary data access as a separate failure. This remains a fixed-source CSV tool workflow, not general desktop automation. Source and recorded results are included in this repository.

Publication note: code, all earlier failure traces, declared cases and aggregate report artifacts are included in this source update. Model inference was run locally; CI runs regression tests rather than downloading model weights.
