# Payload Sources (GTK Prototype)

The payload catalog in `prototype/gtk_shell/payloads.py` is a mix of:

- Technique payloads grounded in official guidance (e.g., OWASP LLM Top 10) and vendor research (e.g., Lakera).
- Benchmark-aligned harmful-request prompts (category-aligned to published datasets such as JailbreakBench).

## Display-Only Provenance Metadata

Some payload entries include optional metadata fields like `source`, `source_url`, `technique`, and `benchmark_*`.

- This metadata is displayed in the prototype UI details pane.
- Only the `text` field is used when composing prompts.

## Primary References

- OWASP Top 10 for LLM Applications: https://genai.owasp.org/llm-top-10/
- OWASP project page: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- NIST AI RMF: https://www.nist.gov/itl/ai-risk-management-framework
- NIST agent hijacking evaluations blog (2025-01): https://www.nist.gov/news-events/news/2025/01/technical-blog-strengthening-ai-agent-hijacking-evaluations
- JailbreakBench: https://jailbreakbench.github.io/
- JBB-Behaviors dataset: https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors
- HarmBench paper: https://arxiv.org/abs/2402.04249
- AdvBench / universal attacks paper: https://arxiv.org/abs/2307.15043
- Lakera prompt injection research: https://www.lakera.ai/blog/guide-to-prompt-injection
- Lakera direct prompt injections: https://www.lakera.ai/blog/direct-prompt-injections

