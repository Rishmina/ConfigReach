# ConfigReach measured accuracy

Results from the repository's hand-labelled benchmark corpus. Labels are committed before scoring and include deliberately difficult positive and negative examples.

| Task | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| env var discovery | 100.0% | 72.7% | 84.2% | 8 | 0 | 3 |
| feature flags | 50.0% | 100.0% | 66.7% | 2 | 2 | 0 |
| config declarations | 66.7% | 90.9% | 76.9% | 10 | 5 | 1 |
| test evidence | 100.0% | 100.0% | 100.0% | 6 | 0 | 0 |
| branch inference | 53.8% | 100.0% | 70.0% | 7 | 6 | 0 |

**Micro precision:** 71.7%  
**Micro recall:** 89.2%  
**Micro F1:** 79.5%  
**Macro F1:** 79.6%

## Errors exposed by the benchmark

### Env Var Discovery

- False positives: none
- False negatives: `DYNAMIC_TOKEN`, `GO_DYNAMIC`, `JS_DESTRUCTURED`

### Feature Flags

- False positives: `coefficient-of-variation`, `stddev`
- False negatives: none

### Config Declarations

- False positives: `name`, `project.name`, `project.version`, `scripts.test`, `version`
- False negatives: `service.mode`

### Test Evidence

- False positives: none
- False negatives: none

### Branch Inference

- False positives: `DEBUG::false`, `DEBUG::true`, `coefficient-of-variation::false`, `coefficient-of-variation::true`, `stddev::false`, `stddev::true`
- False negatives: none

## Label policy

- **env var discovery:** Runtime environment-variable inputs that a human reviewer can identify from source, including statically recoverable intent expressed through simple indirection; declarations alone do not count.
- **feature flags:** Runtime boolean/variant flag lookups whose call is semantically a feature-flag decision; unrelated methods named variation do not count.
- **config declarations:** Declarations of application/runtime/deployment configuration. Package/project metadata such as package.json name/version/scripts and pyproject project metadata do not count.
- **test evidence:** Configuration keys for which a human reviewer can see a test intentionally supplies or exercises the key, including a small helper abstraction.
- **branch inference:** Explicit configuration-dependent decision states. A finite boolean type without an actual decision branch does not itself count as a branch.

## Reproduce

```bash
python validation/accuracy/run_accuracy.py --corpus validation/accuracy/corpus.json --json validation/results/accuracy.json --markdown validation/results/accuracy.md
```

This corpus is intentionally small and transparent. It measures the committed cases exactly; it is not claimed to estimate all repositories or all configuration frameworks.
