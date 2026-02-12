# img2img 기반 Identity Lock 파이프라인

게임용 픽셀 캐릭터를 **아이덴티티를 고정한 채 파츠만 바꿔** 반복 생성하기 위한 파이프라인 설명·워크플로·검증·확장 포인트 정리.

---

## 1. img2img 기반 캐릭터 고정 파이프라인 설명

### 목적
- **txt2img 단일 패스**: 매번 캐릭터가 달라져 일관성 부족.
- **해결**: 생성 결과 1장을 “기준 캐릭터”로 두고, **img2img로만** 파츠(헤어/상의/하의/신발/손 아이템)를 바꾼다.
- **아이덴티티 결정 주체**: 프롬프트가 아니라 **기준 이미지**. denoise 0.35~0.45로 이미지 구조를 유지하고, 프롬프트는 “무엇을 바꿀지”만 지정.

### 흐름
1. **1회만 txt2img**  
   - 해상도 512×512, denoise 1.0으로 베이스 캐릭터 1장 생성.  
   - 이 이미지를 “기준 캐릭터”로 저장.
2. **이후 전부 img2img**  
   - 기준 이미지를 입력으로 업로드.  
   - denoise **0.35 ~ 0.45** (권장 0.4), cfg **6.5 ~ 7**.  
   - 프롬프트: 파츠만 기술 (헤어/상의/하의/신발/아이템/표정).  
   - 결과: 얼굴·눈·머리 비율·체형은 유지, 의상·액세서리만 변경.

### 금지·허용 키워드
- **사용 금지**: `masterpiece`, `best quality`, `ultra detailed` (일러스트 풍 보정 유도).
- **허용 목적형 키워드**:  
  `pixel game character sprite`, `flat colors`, `simple shading`, `clear outline`, `game asset`, `front view`, `standing pose`.

### 파라미터 가이드
| 항목 | txt2img (베이스 1회) | img2img (파츠 변경) |
|------|----------------------|----------------------|
| resolution | 512×512 | 512×512 (입력과 동일) |
| sampler | dpmpp_2m | dpmpp_2m |
| scheduler | karras | karras |
| steps | 25 | 25 |
| cfg | 7.5~8.5 | **6.5 ~ 7** |
| denoise | **1.0** | **0.35 ~ 0.45 (권장 0.4)** |

---

## 2. ComfyUI 워크플로우 구조 (노드 레벨)

### txt2img (베이스 1회): `pixel_character`
- **EmptyLatentImage** (512×512) → **VAEEncode** 없이 **KSampler** latent 입력.
- **CheckpointLoaderSimple** → model, clip, vae.
- **CLIPTextEncode** (positive, negative) → **KSampler**.
- **KSampler** (denoise 1.0, dpmpp_2m, karras, steps 25~30, cfg 7.5~8.5) → **VAEDecode** → **SaveImage**.

### img2img (Identity Lock): `img2img_character`
- **LoadImage** (`__IMAGE_INPUT__`: 업로드한 기준 이미지) → 픽셀 입력.
- **CheckpointLoaderSimple** (`__CKPT_NAME__`) → model, clip, vae.
- **VAEEncode**: LoadImage 픽셀 + VAE → latent.
- **CLIPTextEncode** (positive `__PROMPT__`, negative `__NEGATIVE__`) → **KSampler**.
- **KSampler**:  
  - `latent_image`: VAEEncode 출력  
  - `denoise`: `__DENOISE__` (0.4)  
  - `cfg`: `__CFG__` (6.5~7)  
  - `sampler_name`: dpmpp_2m, `scheduler`: karras, `steps`: 25  
- **VAEDecode** → **SaveImage** (`__FILENAME_PREFIX__`).

노드 연결 요약:
```
LoadImage → VAEEncode (pixels); Checkpoint → VAEEncode (vae)
Checkpoint → CLIPTextEncode(×2) → KSampler
VAEEncode → KSampler (latent_image) → VAEDecode → SaveImage
```

---

## 3. Python 제어 스크립트 예시

### 설정 JSON (img2img 사용 시)
`configs/example_character.json`에서 **base_image**에 기준 이미지 경로를 넣으면 img2img로 동작.

```json
{
  "base_character": {
    "name": "hero_01",
    "seed": 42,
    "ckpt_name": "pixelstyleckpt_strength07.safetensors",
    "cfg_img2img": 6.75,
    "base_prompt": "pixel game character sprite, flat colors, simple shading, clear outline, game asset, front view, standing pose"
  },
  "base_image": "outputs/hero_01_short_black_hair_red_jacket_blue_pants_white_sneakers_empty_neutral_00003_.png",
  "parts": {
    "hair": "short black hair",
    "top": "blue jacket",
    "bottom": "blue pants",
    "shoes": "white sneakers",
    "item": "empty",
    "expression": "neutral"
  },
  "negative_prompt": "lowres, worst quality, blur, soft, gradient, multiple characters, bad anatomy"
}
```

### 실행
```bash
# 베이스 1장 생성 (txt2img) — base_image 비움
python run_character_pipeline.py configs/example_character.json

# 같은 캐릭터로 파츠만 변경 (img2img) — base_image에 위 경로 설정 후
python run_character_pipeline.py configs/example_character.json --seed 42 --denoise 0.4
```

### 코드 레벨 (run_pipeline)
- `base_image` 있음 → 이미지 업로드 후 `img2img_character` 템플릿, placeholders에 `__IMAGE_INPUT__`, `__DENOISE__`, `__CFG__` 설정.
- `base_image` 없음 → `pixel_character` 템플릿, txt2img 1회.
- 프롬프트는 `build_prompt_from_config(..., for_img2img=True)` 시 금지 키워드 제거·목적형만 유지.

---

## 4. “같은 캐릭터로 보이는지” 검증 기준

- **통과**
  - 얼굴 형태·눈 위치·눈 비율이 기준 이미지와 동일/매우 유사.
  - 머리 비율(두상 대 몸통)이 유지됨.
  - 전체 체형(키, 어깨-허리-다리 비율)이 유지됨.
  - 변경한 파츠(상의/하의/신발/아이템)만 다르고 나머지는 동일 인물처럼 보임.
- **실패**
  - 얼굴이 달라 보임 (눈/코/입 위치·형태 변경).
  - 머리/몸 비율이 확 바뀜.
  - 체형이 다른 캐릭터처럼 보임.
- **조치**
  - 실패 시 denoise를 **0.35 쪽으로 낮추기** (이미지 유지 강화).  
  - 과도하게 낮으면 의상 변경이 잘 안 되므로, 0.35~0.45 구간에서 캐릭터별로 한 번씩 튜닝 권장.

---

## 5. 향후 LoRA / ControlNet 확장 가능 포인트

- **LoRA**
  - **위치**: CheckpointLoaderSimple 다음에 **LoraLoader** 노드 추가.  
  - model/clip에 LoRA 적용 후 동일 model/clip을 KSampler·CLIPTextEncode에 전달.  
  - 템플릿에 `__LORA_NAME__`, `__LORA_STRENGTH__` 플레이스홀더 추가, 설정/CLI에서 지정 가능하게 하면 됨.
- **ControlNet**
  - **위치**: KSampler 직전에 **ControlNetApply** (또는 Apply ControlNet) 노드.  
  - ControlNet 모델 로드 노드 + 사전처리(예: Canny, Depth) 결과를 적용해 포즈/구도 고정.  
  - “정면 스탠딩”을 더 안정적으로 쓰고 싶을 때 유용.  
  - 템플릿에 ControlNet 전용 노드 그룹을 추가하고, `control_net_enabled`, `control_net_preprocessor` 등만 바꿀 수 있게 하면 확장 용이.
- **공통**
  - 새 노드들은 `node_templates/`에 별도 JSON으로 두고, `modes`에 합치거나 `connections`로 기존 img2img 체인에 연결하면 됨.

---

## 범위 제한 (절대 금지)
- 애니메이션 생성 ❌  
- 배경 생성 ❌  
- 월드/맵 ❌  
- 멀티 포즈 ❌  
- 일러스트풍 보정 키워드 ❌  

이 파이프라인의 목표는 **“잘 나온 그림”**이 아니라 **실제 서비스에 쓸 수 있는 캐릭터 자산을 안정적으로 만드는 것**이다.
