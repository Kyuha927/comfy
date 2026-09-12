# ONE-SHOT WORK HANDOFF — Storage Regression / Offloader / Hourly Repair

## Model routing
- MAIN root-cause owner: **GPT-5.6 Sol — XHigh**
- Implementation/debugging: **GPT-5.6 Sol — High**
- Independent data-safety/failure-mode auditor: **GPT-6 Astra — XHigh**
- Fault injection/regression/meters: **GPT-5.6 Terra — High**
- Logs/storage counters/inventory: **GPT-5.6 Luna — Medium**
- No Pro in Work.

Take ownership of the macOS storage/offloading/hourly-repair reliability problem. Prior evidence showed disk space could continue falling materially even after apparent scraper/uploader success, so process exit status is not proof.

Recover scripts, launchd config, rclone/offloader logic, logs, storage measurements, repair/debug bundle, current index/concurrency behavior, and prior analysis.

Hard invariant: never delete a local source until the remote copy is proven byte-identical and safely restorable.

Investigate actual byte deltas, incremental behavior, duplicate work, temp/cache/log growth, partial/interrupted uploads, reboot, network loss, Drive quota, ENOSPC, stale state, hash mismatch, restore, retries, backpressure, hysteresis, and concurrency races.

Sol finds root causes and implements fixes. Terra performs fault injection and measured regressions. Luna gathers logs/counters. Astra independently audits data-loss paths and assumptions.

Run real discriminating tests and measure storage behavior. Final report must state root causes, fixes, byte/disk evidence, restore/data-safety proof, and residual risk. Do not declare completion from green logs alone.