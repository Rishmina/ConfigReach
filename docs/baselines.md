# Baselines

Baselines allow existing repositories to adopt ConfigReach without failing CI on every historical gap.

Create a baseline of currently uncovered keys:

```bash
configreach baseline create .
```

The default file is `.configreach/baseline.json`. Baseline keys remain visible in reports with `baseline_ignored: true`, but are excluded from key coverage and CI gating.

To baseline every discovered key instead of only uncovered keys:

```bash
configreach baseline create . --all
```

A baseline is intentionally key-based and human-readable. Remove entries as test coverage improves. New configuration keys are not automatically added, so new gaps remain visible in pull requests.
