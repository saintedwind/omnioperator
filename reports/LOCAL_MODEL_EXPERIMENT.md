# Local model experiment, 2026-10-17

Published baseline: https://github.com/saintedwind/omnioperator/commit/83013c3f18326677aef914b8cf24e4f78f23e1e9
CI: https://github.com/saintedwind/omnioperator/actions/runs/39012891132 (Python 3.9 and 3.12 passed).

The subsequent local experiment uses the existing Qwen3-0.6B Q8_0 GGUF with llama.cpp b11476 on CPU. Model identity and checksum are in live-model.json. It makes actual HTTP inference requests, records returned token usage, and uses the real UCI CSV workflow with independent final-file checks. Model weights are not distributed.

Three prompt iterations were tried: basic instructions, two few-shot examples, and explicit state/transition instructions. Each iteration ran the same three task formulations. They are development probes, not an independent held-out benchmark. None completed all required actions successfully: final iteration 0/3. Early completion and execution before selection were observed. The verifier recorded failure instead of accepting the model's completion claim. All raw model responses and actions are retained in live-model-initial.json, live-model-fewshot.json and live-model.json.

This demonstrates a working inference connection, not a capable autonomous planner. It does not establish that every 0.6B model fails or that prompt tuning cannot help. The current model/prompt configuration is unsuitable for claiming reliable task execution. Next work should compare a stronger local instruction model using predeclared tasks and include unsupported requests; no new weights were downloaded in this experiment.

To reproduce, start a compatible llama.cpp server separately on 127.0.0.1:8081 with /v1/chat/completions, then run `python -m scripts.live_model` from the project root. The adapter rejects non-loopback endpoints and redirects. The runner owns and stops only the runtime it started. No paid API was used. Current experimental source is local; the published 0.2 baseline remains unchanged.
