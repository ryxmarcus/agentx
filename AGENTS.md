# Efficient context and durable memory

- Use targeted retrieval before reading large knowledge documents or transcripts: `python scripts/search_knowledge.py "specific query" --top 3 --json`. Read cited source lines only when needed.
- Do not load full activity logs, transcripts, reports or repository trees into context by default. Start with filenames, bounded searches and excerpts.
- Keep durable facts in `knowledge-base/AGENT-MEMORY.md` and detailed evidence in linked reports. Read only relevant sections. Preserve existing memory; consolidate duplicate facts rather than appending repeated summaries.
- After substantial work, update `knowledge-base/CURRENT-HANDOFF.md` with the current objective, confirmed changes, validation, blockers and next steps. Replace stale task state instead of accumulating conversation history.
- Record evidence dates and distinguish observed facts from assumptions. Recheck live cloud state before changes; memory is a guide, not current infrastructure truth.
- Never save private keys, passwords, tokens, credentials or raw secret-bearing transcripts into memory. Record credential identifiers or paths only.
- Keep tool output bounded and responses concise. Delegate only when explicitly requested. Do not repeat successful checks unless changes or new evidence justify them.
- Persistent files extend retrievable knowledge, not the model's context window. Never claim a token reduction measurement without comparing actual usage.
