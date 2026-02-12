# 프로젝트 설명 및 현재 작업 정리 (Antigravity 핸드오프)

## 1. 프로젝트 개요

**이름**: ComfyUI 2D 게임 캐릭터 자동 생성 파이프라인

**목적**: 로컬 ComfyUI 서버(`http://127.0.0.1:8188`)를 HTTP/WebSocket API로 제어해서, 2D 사이드스크롤 게임용 픽셀 캐릭터 이미지를 **설정(JSON) 기반으로 자동 생성·관리**하는 것.

- **템플릿 기반 워크플로 조립**: `node_templates/` 안 JSON 조각을 로드해 병합, 노드 ID는 1000 단위 오프셋으로 충돌 방지.
- **자동 연결**: `connect()` 헬퍼로 노드 출력→입력 연결.
- **주요 함수**: `comfy_workflow.build_workflow(config)`, `comfy_workflow.generate_image(workflow)`.
- **플레이스홀더**: `__PROMPT__`, `__SEED__`, `__CKPT_NAME__`, `__STEPS__`, `__CFG__` 등 지원.
- **Identity Lock**: img2img(denoise 0.35~0.45)로 캐릭터 유지하면서 파츠만 바꾸는 흐름 지원.

**기술 스택**: Python, `requests`, `websocket-client`, ComfyUI 로컬 서버. 이미지는 `./outputs/`에 저장.

---

## 2. 디렉터리/파일 구조 (핵심만)

| 경로 | 설명 |
|------|------|
| `comfy_workflow.py` | 템플릿 로드·병합·오프셋, 노드 연결, 플레이스홀더 치환, `/prompt` 전송, WebSocket 대기, `/history`·이미지 저장. `get_available_checkpoints(server)` 포함. |
| `run_character_pipeline.py` | JSON 설정 로드 → 프롬프트 조합 → `build_workflow` + `generate_image` 호출. CLI: `--seed`, `--denoise`, `--ckpt`, `--server`. |
| `run_compare_three_ckpts.py` | **3개 체크포인트 비교 스크립트** (아래 “현재 작업” 참고). |
| `node_templates/` | `pixel_character.json`(txt2img 512×512), `img2img_character.json`, `text2img.json`, `upscale.json`, `controlnet.json`. |
| `configs/` | `compare_two_ckpts.json`(비교용 설정), `example_character.json`, 기타 캐릭터 설정. |
| `configs/compare_two_ckpts.json` | 비교 작업에 쓰는 프롬프트·steps·cfg·sampler 등. `base_image` 없음 → txt2img. |
| `start_comfyui_gpu.bat` | `C:\Users\jhk92\Downloads\comfyUI` 로 이동 후 `venv\Scripts\python.exe main.py` 실행 (GPU 사용). |
| `check_comfyui.py` | 8188/8000 포트 연결 여부 확인. |

ComfyUI **실행 파일/서버는 이 repo에 없음**. `C:\Users\jhk92\Downloads\comfyUI` 등 사용자 환경에서 별도 실행 필요.

---

## 3. 현재 하려는 작업: “3개 모델 비교”

**목표**: 아래 3개 SDXL 체크포인트를 **동일 프롬프트·동일 설정**으로 각각 **시드 100, 101, 102**에 대해 1장씩 생성해, 총 **9장**을 만들고 비교.

- `animagine-xl-3.1.safetensors`
- `Illustrious-XL-v2.0.safetensors`
- `SDXLAnimeBulldozer_v20.safetensors`

**실행 방법**  
- 스크립트: `python run_compare_three_ckpts.py`  
- 배치: `run_compare_three_ckpts.bat`  
- 설정: `configs/compare_two_ckpts.json` (steps 28, cfg 7.5, dpmpp_2m, karras 등)

**동작 요약**  
1. `get_available_checkpoints(server)` 로 ComfyUI `/models/checkpoints` 에서 목록 조회.  
2. 선호 체크포인트 3개 중 서버에 있는 것만 사용; 없으면 사용 가능한 체크포인트 상위 3개로 대체.  
3. 체크포인트별 × 시드별로 `run_character_pipeline.run_pipeline(CONFIG, seed_override=, ckpt_override=)` 호출.  
4. 성공 시 `outputs/` 에 저장된 경로 출력, 실패 시 예외 잡아서 건너뛰고 계속 진행.  
5. 마지막에 **성공 건수 / 실패 건수** 출력.

---

## 4. 현재 문제 (실패 원인)

- **증상**: 9건 모두 **실패**. `generate_image()` 반환값이 빈 리스트.  
- **ComfyUI 쪽**: `/history/{prompt_id}` 응답에서 `status` 는 `completed` 인데, **`outputs` 가 비어 있음** (`outputs노드=[]`).  
- **해석**: 워크플로는 큐에 들어가고 “실행 완료”로 처리되지만, **실제로는 SaveImage 노드까지 실행되지 않았거나**, 실행 결과가 history의 `outputs` 에 들어오지 않는 상태.  
  - 즉, **실행이 중간에 실패**(체크포인트 로드 실패, OOM, 노드 오류 등)했거나,  
  - **ComfyUI 버전/API 차이**로 history 구조가 달라서 우리가 기대하는 `outputs` 형태가 아님.

**이전에 시도한 대응**  
- `comfy_workflow.generate_image`: 이미지 0장일 때 `outputs` / `output` 키 둘 다 확인, status·outputs 노드 ID를 에러 메시지에 포함.  
- `run_compare_three_ckpts.py`: 실패 시 예외만 로그하고 다음 항목 계속 실행, 마지막에 성공/실패 개수 출력.  
- ComfyUI에 있는 체크포인트만 쓰도록 `get_available_checkpoints` 연동.

**아직 확인 안 된 것**  
- ComfyUI **콘솔(터미널) 로그**에 체크포인트 로드 실패/노드 오류 등이 찍히는지.  
- 사용자 ComfyUI의 **history 응답 실제 구조** (예: `outputs` 키 이름, 노드 ID 형식, 이미지 정보 위치).  
- `models/checkpoints` 에 위 3개 파일이 **정확한 파일명**으로 존재하는지.

---

## 5. Antigravity가 하면 좋을 것 (다음 단계 제안)

1. **ComfyUI history 구조 확인**  
   - `generate_image` 내부 또는 별도 스크립트에서 `/history/{prompt_id}` 원본 JSON을 한 번 로그/파일로 저장해, 실제 키(`outputs` / `output` / 기타)와 노드별 구조 확인.  
   - 필요하면 해당 구조에 맞춰 “이미지가 있는 노드”를 찾고, 그 노드의 이미지만 저장하도록 로직 수정.

2. **실행 실패 원인 수집**  
   - WebSocket으로 `execution_error` 등 메시지를 받아 로그에 남기거나,  
   - ComfyUI 콘솔 로그를 사용자에게 요청해, 체크포인트 로드 실패/OOM/노드 에러 중 무엇인지 파악.

3. **체크포인트·워크플로 검증**  
   - `/models/checkpoints` 목록과 비교 스크립트에서 요청하는 파일명이 일치하는지 확인.  
   - 필요하면 ComfyUI 웹 UI에서 같은 체크포인트·같은 해상도(512×512)로 수동 1장 생성해 보며, 그때는 정상 동작하는지 확인.

4. **비교 작업이 끝난 뒤**  
   - 9장이 정상 생성되면 `outputs/` 에서 파일명·체크포인트별로 정리해 비교 가능하게 하거나, 사용법을 README에 한 줄 추가하는 정도까지 하면 좋음.

---

## 6. 실행 시 유의사항

- **ComfyUI 서버**가 `http://127.0.0.1:8188` 에 떠 있어야 함. (`start_comfyui_gpu.bat` 또는 사용자 환경에서 실행.)  
- **작업 디렉터리**는 이 repo 루트(`comfy`)로 두고 실행. (PowerShell에서 경로에 한글이 있으면 `Set-Location` 이 실패할 수 있음 – 필요 시 경로 짧게 하거나 cmd 사용.)  
- 비교 스크립트는 **실패해도 중단하지 않고** 9건 모두 시도한 뒤 “성공: N, 실패: M” 출력.

---

## 7. 요약 한 줄

**프로젝트**: ComfyUI API로 2D 게임용 캐릭터 이미지 자동 생성하는 파이썬 모듈.  
**지금 할 일**: Animagine XL 3.1 / Illustrious-XL / Bulldozer 3개 체크포인트를 동일 설정·시드 100,101,102로 각 1장씩 생성(총 9장).  
**현재 상태**: 9건 모두 ComfyUI history에서 `outputs` 가 비어 있어 0장만 저장됨. 원인(실행 실패 vs history 구조 차이) 파악 및 수정이 필요함.
