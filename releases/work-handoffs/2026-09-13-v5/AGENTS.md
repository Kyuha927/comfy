# Scoped Agent Rule — LIN ASTER 3D Handoffs

Before executing, continuing, reviewing, or reporting on any LIN ASTER 3D, Tripo, Blender control-plane, Blender Pro Bridge, Mobile Hero, or Production Skill OS handoff in this directory, read the current project SSOT:

`https://github.com/Kyuha927/lastline-echoes/blob/lin-aster-tripo-r01-20260913/work/handovers/2026-09-13/00_READ_FIRST_LIN_ASTER_3D_ROUTE.md`

Also read the machine state when automation or structured routing is involved:

`https://github.com/Kyuha927/lastline-echoes/blob/lin-aster-tripo-r01-20260913/work/handovers/2026-09-13/LIN_ASTER_3D_LIVE_STATE.json`

Rules:

1. Re-read the SSOT before any completion, merge, canon, production-readiness, or next-step claim.
2. Do not reconstruct current state from chat memory when the SSOT is available.
3. Do not overwrite a newer SSOT from a stale commit.
4. Preserve candidate, tested candidate, production canon, and user-approved final as separate states.
5. Existing Bridge acceptance workspaces and exact candidate identities remain frozen unless the SSOT explicitly changes them.
6. If the SSOT cannot be accessed, stop with `BLOCKED_CURRENT_3D_SSOT_UNAVAILABLE`.
