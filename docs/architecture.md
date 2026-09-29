# Architecture

ConfigReach separates **discovery**, **coverage evidence**, and **reporting**.

1. `discover.py` walks repository files using explicit ignore rules.
2. Python source is parsed with `ast`; other language environment reads use conservative patterns.
3. Declaration adapters inspect dotenv, JSON, TOML, INI, YAML, Terraform and Make files.
4. Test files contribute key-level coverage evidence and, when assignments are statically visible, value-level evidence.
5. `models.py` stores provenance for every read, declaration and test mention.
6. `reporters.py` converts the same deterministic model into text, JSON, Markdown or SARIF.
7. `tracer.py` provides an optional Python-only runtime trace that fingerprints values instead of storing them.

## Design rules

- Offline and CPU-only by default.
- No model or API call in the core engine.
- Every finding retains source provenance.
- Unknown is preferable to fabricated certainty.
- Language support levels are documented honestly.

## Adapter roadmap

The initial release has deep Python environment/CLI parsing and conservative cross-language environment-read detection. Future adapters can add AST-backed JavaScript/TypeScript, Go, Java and Rust analysis without changing the report model.
