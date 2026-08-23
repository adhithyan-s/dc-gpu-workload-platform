# Data Quality Notes

Findings from exploring the raw trace data, and the reasoning behind how `pipeline/transforms/validate_pod_list.py` handles each one.

## `gpu_spec` is null for all 8,152 rows - expected, not an error

Per Alibaba's own docs, null means "no GPU-type constraint". Every pod in `openb_pod_list_default.csv` happens to have no constraint - the GPU-type-specific behavior lives in a different variant file we're not using. The validator treats this column as always-nullable, not "sometimes nullable".

## `scheduled_time` is null only for `Pending` pods - expected

897 rows have a null `scheduled_time`, and all 897 are `pod_phase == "Pending"` - logically correct: a pod that's still pending was never scheduled, so it should have no scheduled time. The validator checks this conditionally (`check_scheduled_time_nulls_match_pending`) rather than a blanket "never null" rule - a null here is only a problem if the pod *isn't* Pending.

## One anomaly: `openb-pod-1523` has `memory_mib == 0`

A `Succeeded` pod (it actually ran and completed) declaring zero memory. This is genuinely unusual - every other row has positive memory - but:
- It's 1 row out of 8,152 (0.01%).
- It's not obviously wrong; it could be a real edge case in Alibaba's own data collection (e.g. a job that only used GPU memory, not host memory).

**Decision:** treated as a `WARNING`, not an `ERROR` - flagged in the validation report, but doesn't block the pipeline. If this becomes a problem later (e.g. it breaks a feature calculation that divides by memory), we can revisit and drop the row explicitly, with the reason documented at that point rather than silently filtering it now.

## Everything else checked out clean

No duplicate pod names, no `deletion_time` earlier than `creation_time`, no negative GPU fields, no non-positive `cpu_milli`, all `qos` and `pod_phase` values match the known set from Alibaba's docs. See `validate_pod_list.py` for the exact checks.