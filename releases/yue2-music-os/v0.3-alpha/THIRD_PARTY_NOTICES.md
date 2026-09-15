# Third-party notices

## YuE2 project helper adaptation

`src/yue2_music_os/abc_tools.py` is adapted from `skills/yue2-music/scripts/abc_tools.py` in the YuE2 project by the YuE2 authors. The upstream helper, code, skill, and documentation are licensed under Apache License 2.0. Changes include packaging, typing, harmony-difference reporting, and removal of the standalone CLI.

Upstream project: `multimodal-art-projection/YuE`

Reviewed upstream code commit: `88da114a67df892af0329472073b96a5ef700b93`

This repository does not include YuE2, YuE2 VAE, MERT2, or SheetSage2 model weights. Those resources and all Python dependencies retain their own licenses and notices. At the time this alpha was prepared, the checked public model-weight terms were noncommercial. Operators must review the exact model snapshot license they install.

## YuE project mark

`src/yue2_music_os/static/yue2-mark.svg` wraps a size-normalized copy of the YuE project mark supplied with the task and matching the upstream project's `assets/logo.png`. It is used only to identify the integration. All trademark and branding rights remain with their respective owner, and no upstream endorsement is claimed.


## Optional Spotify Basic Pitch adapter

The Note IR layer can optionally import `basic-pitch` at runtime or invoke an isolated command wrapper. Basic Pitch is not bundled with this distribution. The upstream source is Copyright 2022 Spotify AB and licensed under Apache License 2.0. Operators must preserve upstream notices and verify the exact installed package, model, and dependency terms.

Upstream project: `spotify/basic-pitch`
