# ONE-SHOT HANDOFF — COMPLETE BLENDER PRO BRIDGE 0.5.0a2 FULL MAC ACCEPTANCE

## Routing

- Preserve the receiving chat's current main model and reasoning level.
- Keep the just-used review split unless the receiving chat already has a stronger approved route:
  - Astra XHigh: test selection, final evidence review, acceptance decision.
  - Terra High: bounded execution/evidence interpretation if already available in this chat.
  - GPT-5.6 Sol High: use only if a reproducible implementation defect is proven and a code correction is actually required.
- Do not spawn additional workers merely to parallelize this acceptance run.
- Record requested and actually used model/profile/effort in the final receipt. No silent fallback.

## Global handoff policy

Follow the user's global handoff policy as the controlling process policy:

`https://github.com/Kyuha927/noin-webgpt-system-audit/blob/main/GLOBAL_PROMPT_HANDOFF_POLICY.md`

## Mission

Continue directly from the completed discrimination run and execute the **full unchanged Blender Pro Bridge `0.5.0a2 LOCAL_ACCEPTANCE` path on the approved Mac host**.

Do not spend another cycle trying to explain the historical `-11` SIGSEGV before the full acceptance run. The historical failure remains preserved and unresolved, but the current approved host has just passed the minimum discriminating tests.

The goal of this handoff is to answer one question:

> Does the exact unchanged `0.5.0a2` candidate complete its full local native acceptance path on the current approved Mac, including real Blender mutation, rendered-pixel evidence, save/reopen, revision safety, retry/discard behavior, and restore/rollback?

This is still candidate validation. It does **not** authorize production replacement, canon promotion, PR merge, or modification of the LIN ASTER production asset.

---

# 1. PRESERVE THE JUST-COMPLETED EVIDENCE

Treat the following reported state as immutable prior evidence, not something to rewrite:

- same Blender executable: `Blender 4.5.4 LTS`;
- executable SHA-256:
  `a9b20b92899646bdc50ea455543cdec098b81d754f88d20145f908a953e8d32d`;
- direct minimal launch: PASS;
- unchanged `0.5.0a2` supervisor/resource-limit path with the same minimal Blender arguments: PASS;
- unchanged bootstrap/runner initialization path, isolated run #1: PASS;
- unchanged bootstrap/runner initialization path, isolated run #2: PASS;
- both initialization runs: no `failure.json`;
- no matching new macOS crash report observed;
- exact `0.5.0a2` runtime 34-file hash verification: PASS;
- startup files and tracked source unchanged;
- prior historical `-11` / SIGSEGV: `PRIOR_FAILURE_NOT_REPRODUCED_ON_APPROVED_HOST`;
- historical failure cause: `UNRESOLVED`;
- previous exact external condition included `workspace-write`; current approved execution metadata is `danger-full-access`; this difference is evidence only, not a proven cause.

Do not delete, overwrite, relabel, or retroactively reinterpret the old failed evidence.

Do not modify settings merely to recreate `workspace-write` before the full acceptance run.

---

# 2. AUTHORITATIVE CANDIDATE

Use the exact existing `0.5.0a2 LOCAL_ACCEPTANCE` package and its normal entry path.

Authoritative candidate reference:

`https://github.com/Kyuha927/angrydino-visual-handoff/blob/e8095fea25cb2f8a1eb56dcb2b7be442d5ffa854/validation/blender-unified/START_HERE.md`

Known package identity from prior validation:

- package: `Blender_Pro_Bridge_0.5.0a2_LOCAL_ACCEPTANCE.zip`
- package SHA-256:
  `cc996f09d0b0ebdcb5dd957dbbb3d2542b2171dd7bf1b56aa9ea9c0af784a9c2`
- expected normal local entry:
  `START_MAC.command -> start_local.py`

Before execution, verify that the source/package/runtime used for this run still matches the preserved candidate identity. If it does not, stop with `BLOCKED_CANDIDATE_IDENTITY_CHANGED` instead of silently testing a different build.

---

# 3. DO NOT CHANGE THE TEST SUBJECT

For this run:

- do not patch candidate source before the test;
- do not change the production Blender plug-in;
- do not alter the user's original `.blend` files;
- do not import LIN ASTER or any Tripo production candidate yet;
- do not use GUI Computer Use as a substitute for the acceptance program;
- do not add another MCP implementation;
- do not change Blender version;
- do not change the candidate's bootstrap/runner path merely to make the test pass;
- do not promote the candidate to production even if the full run passes.

Use only isolated acceptance workspaces created by the candidate's intended acceptance mechanism.

---

# 4. EXECUTE THE FULL NORMAL MAC ACCEPTANCE PATH

Run the normal `START_MAC.command` acceptance flow from start to terminal result.

Do **not** stop at bootstrap/init this time.

The run must exercise the actual acceptance behaviors exposed by the package, including every applicable capability below that the package's own acceptance harness is designed to validate:

1. start the isolated local acceptance workspace;
2. launch the exact Blender 4.5.4 executable;
3. establish the candidate's stdio/server/bridge path exactly as packaged;
4. create or use only the isolated acceptance scene;
5. perform candidate mesh/material edits required by the harness;
6. preserve request/revision identity;
7. save/checkpoint the candidate scene;
8. create the required fixed-condition renders, including front / side / three-quarter views when the harness requests them;
9. verify that PNG files contain actual rendered bytes, not only paths or success receipts;
10. record PNG size/hash or equivalent pixel-evidence identity when available;
11. exercise review/apply behavior;
12. exercise retry behavior;
13. exercise discard behavior;
14. exercise repeated-edit behavior;
15. verify revision/state transitions after those operations;
16. test any server restart/revocation behavior included in the package;
17. perform fresh-process reopen of the saved acceptance scene where the acceptance path requires it;
18. verify the reopened scene state against the pre-close checkpoint;
19. exercise backup restore / rollback as implemented by the candidate;
20. verify old rendered-preview lookup or historical PNG retrieval where the harness includes it;
21. collect the package's terminal `RESULT.json` and `RESULT.html`;
22. collect `RESULT_SUPPORT.zip` or the package's equivalent support bundle.

Do not invent missing PASS criteria. Use the package's actual acceptance contract and report any contract mismatch explicitly.

---

# 5. FAILURE HANDLING

If the full acceptance run fails:

## A. SIGSEGV / `-11` recurs

Immediately preserve, before any retry:

- exact argv;
- cwd;
- cleaned environment snapshot;
- outer supervisor exit code;
- inner Blender exit code if available;
- timestamp and PID;
- resource-limit record;
- stdout/stderr;
- candidate workspace contents;
- `failure.json` if created;
- matching macOS `.ips` crash report;
- exact executable hash;
- candidate runtime/file hashes.

Classify the event as:

`SIGSEGV_REPRODUCED_DURING_FULL_ACCEPTANCE`

Do not patch anything until the recurrence is compared with the historical failure and a minimal discriminating hypothesis is formed.

## B. A deterministic candidate feature fails without a crash

Preserve the exact request, revision, state DB, rendered evidence, expected/actual output, and failure code.

If the same failure reproduces once under the same input and environment, it may be escalated to Sol High for the **smallest candidate-only correction**.

Any correction must happen on a separate candidate branch/worktree and must not rewrite the evidence from this unchanged `0.5.0a2` run.

## C. Environmental blocker

Return the exact blocker. Do not replace the Blender binary, authentication state, user settings, sandbox mode, or package configuration merely to force continuation.

---

# 6. PASS GATE

A local native acceptance PASS requires all of the following:

- normal `START_MAC.command -> start_local.py` path completes to its documented terminal state;
- no candidate runtime hash drift occurred before the run;
- real Blender 4.5.4 participated;
- required scene mutations completed;
- save/checkpoint completed;
- required actual rendered PNG pixel evidence exists;
- apply/retry/discard/repeated-edit behavior completed where required;
- revision/state behavior is internally consistent;
- fresh-process reopen completed where required by the acceptance contract;
- restore/rollback completed;
- terminal result artifacts were generated and are internally consistent;
- no unexplained crash or hidden fallback occurred.

If all local-native gates pass, classify the result as:

`LOCAL_NATIVE_FULL_ACCEPTANCE_PASS`

Do **not** call it `PRODUCTION_READY`, `FINAL`, `CANONICAL`, or `WEB_VERIFIED`.

The Web ChatGPT path and actual LIN ASTER production E2E remain separate gates.

---

# 7. AFTER A LOCAL PASS

If `LOCAL_NATIVE_FULL_ACCEPTANCE_PASS` is achieved:

1. preserve the exact acceptance evidence bundle and hashes;
2. mark the prior `-11` only as a preserved historical intermittent failure that was not reproduced in the successful full run;
3. keep root cause `UNRESOLVED` unless new evidence actually proves a cause;
4. do not perform speculative code cleanup;
5. do not merge or replace the production bridge automatically;
6. report that the candidate is now ready for the next gate:

```text
selected Tripo LIN candidate
-> Blender import
-> GPT-6 Astra Computer Use supervised visual assembly
-> same-scene Blender Pro Bridge deterministic inspection / exact operations / render evidence
-> save/checkpoint
-> fresh-process reopen
-> rollback/restore
-> user review
```

Do not start that LIN E2E in this acceptance task unless a selected Tripo candidate already exists **and** the user explicitly asks to continue into that separate gate.

---

# 8. WHAT NOT TO DO NEXT

Do not spend time on these before the full acceptance result exists:

- speculative `-11` patching;
- forced recreation of the old sandbox metadata;
- unrelated Bridge feature expansion;
- production canon migration;
- PR merge merely because offline/unit CI passes;
- changing the Tripo/Astra control-plane candidate;
- touching LIN ASTER production assets.

The full native acceptance result is the next information-producing step.

---

# 9. REQUIRED EVIDENCE OUTPUT

Create an isolated output/evidence directory for this run and preserve at minimum:

- `VALIDATION_REPORT.md`
- `DECISION.json`
- full terminal logs;
- candidate identity/hash manifest;
- actual argv/env/cwd/exit-code evidence;
- resource-limit/supervisor evidence;
- Blender version and executable hash;
- state/revision snapshots;
- rendered PNG evidence and hashes where available;
- save/reopen evidence;
- rollback/restore evidence;
- candidate-generated `RESULT.json`;
- candidate-generated `RESULT.html`;
- candidate-generated `RESULT_SUPPORT.zip` or equivalent;
- one final evidence ZIP with per-file SHA-256 manifest and ZIP integrity verification.

Do not overwrite the earlier discrimination-test evidence bundle.

---

# 10. FINAL RESPONSE FORMAT

Return exactly these headings:

1. `STATUS`
2. `CANDIDATE_IDENTITY`
3. `UNCHANGED_SOURCE_VERIFICATION`
4. `FULL_START_MAC_ACCEPTANCE`
5. `REAL_BLENDER_EXECUTION`
6. `SCENE_MUTATION_AND_REVISION`
7. `RENDERED_PIXEL_EVIDENCE`
8. `APPLY_RETRY_DISCARD_REPEATED_EDIT`
9. `SAVE_AND_FRESH_PROCESS_REOPEN`
10. `ROLLBACK_AND_RESTORE`
11. `HISTORICAL_SIGSEGV_STATUS`
12. `FAILURES_OR_BLOCKERS`
13. `RESULT_ARTIFACTS`
14. `FINAL_DECISION`
15. `NEXT_GATE`

`FINAL_DECISION` must be exactly one of:

- `LOCAL_NATIVE_FULL_ACCEPTANCE_PASS`
- `FAIL_REPRODUCIBLE_CANDIDATE_DEFECT`
- `FAIL_SIGSEGV_REPRODUCED`
- `BLOCKED_EXTERNAL`
- `BLOCKED_CANDIDATE_IDENTITY_CHANGED`
- `INCOMPLETE_EVIDENCE`

Never erase the historical failure and never claim production completion from this local acceptance alone.
