# ComfyUI 워크플로 동적 조립 모듈

로컬 ComfyUI 서버(`http://127.0.0.1:8188`)와 HTTP/WebSocket으로 통신하며, JSON 템플릿을 합쳐 워크플로를 동적으로 조립·실행하는 파이썬 모듈입니다. 2D 게임 리소스 자동 생성/관리에 활용할 수 있습니다.

## 설치

```bash
pip install -r requirements.txt
```

## 구조

- **`comfy_workflow.py`** – 핵심 모듈 (템플릿 로드, 오프셋, 연결, 빌드, 실행)
- **`node_templates/`** – JSON 워크플로 조각 (text2img, upscale, **pixel_character** 등)
- **`configs/`** – 캐릭터 파이프라인 설정 JSON (base_character, parts)
- **`outputs/`** – 생성 이미지 저장 경로 (기본)
- **`run_character_pipeline.py`** – 게임용 픽셀 캐릭터 파이프라인 (CLI)
- **`example_usage.py`** – 사용 예시

## 사용법

### 1. 단일 템플릿 실행 (text2img)

```python
import comfy_workflow as cw

config = {
    "modes": ["text2img"],
    "placeholders": {"__PROMPT__": "game character sprite", "__SEED__": 42},
}
workflow = cw.build_workflow(config)
paths = cw.generate_image(workflow, server="http://127.0.0.1:8188")
```

### 2. 템플릿 조합 및 연결 (text2img → upscale)

- `modes`: 사용할 템플릿 순서. 각 템플릿에 **1000 단위 오프셋**이 적용됩니다 (첫 번째 0, 두 번째 1000, …).
- `connections`: 앞 모드의 출력 노드 → 다음 모드의 입력 노드 연결 (오프셋 적용된 노드 ID 사용).

```python
config = {
    "modes": ["text2img", "upscale"],
    "placeholders": {"__PROMPT__": "a cat", "__SEED__": 123},
    "connections": [
        {"from_node": "8", "from_slot": 0, "to_node": "1003", "to_input": "image"}
    ],
}
workflow = cw.build_workflow(config)
cw.remove_node(workflow, "1001")  # 사용하지 않는 LoadImage 제거 (선택)
paths = cw.generate_image(workflow)
```

### 3. 수동 조립 및 `connect` 헬퍼

```python
workflow = cw.merge_templates(["text2img", "upscale"])
cw.connect(workflow, "8", "1003", "image", output_slot=0)
cw.apply_placeholders(workflow, {"__PROMPT__": "a cat", "__SEED__": 42})
paths = cw.generate_image(workflow)
```

### 4. 특정 노드 직접 수정

- `set_node_input(workflow, node_id, key, value)` – 한 입력만 변경
- `update_workflow_by_node_id(workflow, node_id, {"seed": 123, "steps": 30})` – 여러 입력 일괄 변경
- `find_nodes_by_class(workflow, "KSampler")` – class_type으로 노드 ID 찾기

### 5. 플레이스홀더

템플릿 JSON 안에 `__PROMPT__`, `__SEED__`, `__INPUT_IMAGE__` 등을 넣고, `placeholders` 또는 `params[모드명]`에서 치환할 수 있습니다.

---

## 게임용 픽셀 캐릭터 파이프라인 (Identity Lock)

**목적**: **img2img 기반**으로 캐릭터 아이덴티티(얼굴·눈·비율·체형)를 고정하고, **파츠만 바꿔가며** 게임용 스탠딩 캐릭터를 반복 생성.

- **1회 txt2img**: `base_image` 비움 → 512×512 베이스 1장 생성 후, 그 이미지를 “기준 캐릭터”로 저장.
- **이후 img2img**: `base_image`에 기준 이미지 경로 지정 → denoise 0.35~0.45(권장 0.4), cfg 6.5~7로 파츠만 변경.
- **설정**: `configs/example_character.json` – `base_character`, `base_image`, `parts`, `negative_prompt`. 프롬프트는 목적형 키워드만 사용(금지: masterpiece, best quality, ultra detailed).
- **출력**: 512×512, 파일명 `hero_01_{hair}_{top}_{bottom}_{shoes}_{item}_{expression}_0000N_.png`.

상세: [docs/img2img_identity_lock_pipeline.md](docs/img2img_identity_lock_pipeline.md)

### CLI 실행

```bash
# 베이스 1장 생성 (txt2img) — base_image 비워 둔 상태
python run_character_pipeline.py configs/example_character.json

# 같은 캐릭터로 파츠만 변경 (img2img) — base_image에 기준 이미지 경로 설정 후
python run_character_pipeline.py configs/example_character.json --seed 42 --denoise 0.4

# 설정 파일·시드·저장 폴더 지정
python run_character_pipeline.py configs/my_character.json --seed 123 --out ./my_outputs
```

### JSON 설정 예시

`configs/example_character.json`을 복사해 수정. `base_image`를 비우면 txt2img, 경로를 넣으면 img2img. `base_character.ckpt_name`은 ComfyUI `models/checkpoints/` 파일명과 맞출 것.

### 파츠 교체 검증

- **같은 캐릭터로 보이는지**: 얼굴·눈 위치·머리 비율·체형 유지, 변경한 파츠(헤어/상의/하의/신발/아이템)만 다르면 통과.
- **실패 시**: denoise를 0.35 쪽으로 낮추기. 검증 기준은 [docs/img2img_identity_lock_pipeline.md](docs/img2img_identity_lock_pipeline.md) 참고.

### LoRA 확장

- **베이스 캐릭터 고정**: `base_character`에 `lora_name`, `strength` 등을 추가하고, `node_templates/pixel_character.json`에 LoRA 로더 노드를 넣은 뒤 `run_character_pipeline.py`에서 해당 플레이스홀더를 채우면 됨.
- **파츠별 LoRA**: hair/top/bottom 등별로 LoRA를 두고, 설정에서 `parts.hair_lora`처럼 지정한 뒤 워크플로에서 여러 LoRA를 적용하는 노드 체인으로 확장 가능.
- 확장 시 `comfy_workflow.build_workflow`의 `placeholders`에 `__LORA_NAME__`, `__LORA_STRENGTH__` 등을 추가하면 됨.

## API 요약

| 함수 | 설명 |
|------|------|
| `load_template(name)` | `node_templates/{name}.json` 로드 |
| `merge_templates(names)` | 여러 템플릿을 1000 단위 오프셋으로 병합 |
| `apply_offset(template, offset)` | 템플릿 노드 ID에 offset 적용 |
| `connect(workflow, out_id, in_id, input_key, output_slot=0)` | 출력 → 입력 연결 |
| `build_workflow(config)` | config로 최종 워크플로 생성 |
| `generate_image(workflow, ...)` | /prompt 전송, WebSocket 대기, 결과를 `outputs/`에 저장 |
| `apply_placeholders(workflow, replacements)` | `__NAME__` 치환 |
| `set_node_input` / `update_workflow_by_node_id` | 노드 입력 직접 수정 |

## 요구사항

- ComfyUI 서버가 `http://127.0.0.1:8188`에서 실행 중이어야 합니다.
- `node_templates/*.json`은 ComfyUI에서 사용하는 노드 구조와 호환되어야 합니다 (필요 시 Export API로 확인).
