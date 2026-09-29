---
title: ConfigReach
emoji: 🎯
colorFrom: blue
colorTo: green
sdk: static
app_file: index.html
fullWidth: true
header: mini
pinned: false
license: mit
short_description: Deterministic configuration coverage for software repos.
tags:
  - developer-tools
  - testing
  - configuration
  - static-analysis
  - github-actions
  - cpu
  - environment-variables
  - feature-flags
---

# ConfigReach

**Codecov for configuration space.**

ConfigReach is a deterministic, CPU-only configuration coverage analyzer for software repositories. It shows which environment variables, feature flags, CLI options, configuration values, branches, and configuration combinations your tests actually exercise.

## Latest release

**ConfigReach v0.9.1** is published on PyPI.

```bash
pip install --upgrade configreach
```

## Published validation

The current reproducible validation suite scans **10 pinned recognizable open-source projects** and reports:

- **18,016** configuration inputs discovered
- **639** inputs with detected test/runtime evidence
- **3.5%** aggregate observed key coverage across the external-project corpus
- **71.7%** micro precision
- **89.2%** micro recall
- **79.5%** micro F1
- **79.6%** macro F1

The repository also publishes reviewed false-positive/false-negative examples and the exact hand-labelled accuracy corpus. External-project coverage is observational; precision/recall claims come from the labelled benchmark.

## Project links

- [GitHub repository](https://github.com/sauravsingla/ConfigReach)
- [PyPI package](https://pypi.org/project/configreach/)
- [ConfigReach v0.9.1 release](https://github.com/sauravsingla/ConfigReach/releases/tag/v0.9.1)
- [Validation methodology](https://github.com/sauravsingla/ConfigReach/blob/main/VALIDATION.md)
- [Real-world results](https://github.com/sauravsingla/ConfigReach/blob/main/validation/results/real-world.md)
- [Measured accuracy](https://github.com/sauravsingla/ConfigReach/blob/main/validation/results/accuracy.md)
- [GitHub Pages site](https://sauravsingla.github.io/ConfigReach/)

This Space is published automatically from GitHub using Hugging Face Trusted Publishers and GitHub Actions OIDC. No long-lived Hugging Face token is stored in GitHub.
