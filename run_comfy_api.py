import requests
import json
import random

# ComfyUI API Address (RunPod Proxy)
BASE_URL = "https://w2672t3cq8hyic-8188.proxy.runpod.net"
PROMPT_API = f"{BASE_URL}/prompt"

# 1) 로컬에 저장한 workflow JSON 불러오기
# 사용자의 hidream_i1_full.json 파일 경로
JSON_PATH = r"c:\Users\jhk92\Downloads\hidream_i1_full.json"

with open(JSON_PATH, "r", encoding="utf-8") as f:
    workflow = json.load(f)

# --- Improvement Iteration 1: Composition & Detail Enhancers ---
COMPOSITION_BOOSTERS = [
    "cinematic lighting", "dramatic backlighting", "rim lighting", 
    "low angle shot", "extreme close-up", "composition symmetry",
    "volumetric fog", "floating particles"
]

DETAIL_BOOSTERS = [
    "intricate mechanical joints", "exposed hydraulic cables", 
    "coolant steam venting", "micro-chips visible", 
    "scratched metal texture", "weathered armor"
]

def get_enhanced_prompts(base_pos, base_neg):
    # Select random enhancers
    comp = random.choice(COMPOSITION_BOOSTERS)
    detail = random.sample(DETAIL_BOOSTERS, 2)
    
    enhanced_pos = f"{base_pos}, {comp}, {', '.join(detail)}, masterpiece, highly detailed"
    enhanced_neg = f"{base_neg}, out of focus, blurry background, flat lighting"
    return enhanced_pos, enhanced_neg

# 2) 워크플로 안에서 노드 찾아서 파라미터 수정
POS_NODE_ID = "91"
NEG_NODE_ID = "85"
LATENT_NODE_ID = "86"
SAMPLER_NODE_ID = "93"
SAVE_NODE_ID = "90"

BASE_POSITIVE = (
    "score_9, score_8_up, score_7_up, source_anime, pixel art, 16-bit, retro game style, "
    "simple background, white background, 1boy, male focus, villain, ceo, slicked back hair, "
    "black formal suit, torn clothes, (futuristic mechanical armor:1.3), cyborg, half machine face, "
    "robotic parts, mechanical arm, arm cannon, glowing red eyes, "
    "(glowing red arc reactor on chest:1.2), weapon, full body, side view, fighting stance"
)

BASE_NEGATIVE = (
    "(worst quality, low quality:1.4), 3d, realistic, photo, photorealistic, blurry, text, "
    "watermark, signature, monochrome, grayscale, lowres, bad anatomy, bad hands, "
    "missing fingers, extra digit"
)

# 3) ComfyUI API용 payload 구성
print(f"--- Starting Batch Generation (4 Images) ---")

for i in range(4):
    # 시드 및 파라미터 개별 설정
    current_seed = random.randint(1, 1125899906842624)
    workflow[SAMPLER_NODE_ID]["inputs"]["seed"] = current_seed
    workflow[SAVE_NODE_ID]["inputs"]["filename_prefix"] = f"pixel_ceo_villain_batch_{current_seed}"
    
    payload = {"prompt": workflow}
    
    print(f"[{i+1}/4] Sending Seed: {current_seed}...")
    try:
        res = requests.post(PROMPT_API, json=payload, timeout=30)
        res.raise_for_status()
        result = res.json()
        print(f"    SUCCESS: Prompt ID {result.get('prompt_id')}")
    except Exception as e:
        print(f"    ERROR: {e}")

# --- Improvement Iteration 2: Technical Diversity ---
ASPECT_RATIOS = {
    "square": (768, 768),
    "portrait": (768, 1024),
    "cinematic": (1024, 768)
}

# 3) 배치 생성 실행
print(f"--- Starting Enhanced Batch Generation (4 Images) ---")

for i in range(4):
    current_seed = random.randint(1, 1125899906842624)
    ar_name, (width, height) = random.choice(list(ASPECT_RATIOS.items()))
    
    # Apply Iteration 1: Enhanced Prompts
    pos, neg = get_enhanced_prompts(BASE_POSITIVE, BASE_NEGATIVE)
    
    workflow[POS_NODE_ID]["inputs"]["text"] = pos
    workflow[NEG_NODE_ID]["inputs"]["text"] = neg
    workflow[SAMPLER_NODE_ID]["inputs"]["seed"] = current_seed
    workflow[LATENT_NODE_ID]["inputs"]["width"] = width
    workflow[LATENT_NODE_ID]["inputs"]["height"] = height
    
    # CFG/Steps Tweak based on aspect ratio (Technical Diversity)
    workflow[SAMPLER_NODE_ID]["inputs"]["steps"] = 28 if ar_name != "square" else 24
    workflow[SAMPLER_NODE_ID]["inputs"]["cfg"] = 8.0 if "lighting" in pos else 7.0
    
    workflow[SAVE_NODE_ID]["inputs"]["filename_prefix"] = f"pixel_ceo_v2_{ar_name}_{current_seed}"
    
    # 4) ComfyUI API용 payload 구성 및 요청
    payload = {"prompt": workflow}
    
    print(f"[{i+1}/4] AR: {ar_name} | Seed: {current_seed}...")
    try:
        res = requests.post(PROMPT_API, json=payload, timeout=30)
        res.raise_for_status()
        result = res.json()
        print(f"    SUCCESS: Prompt ID {result.get('prompt_id')}")
    except Exception as e:
        print(f"    ERROR: {type(e).__name__}")

# --- Improvement Iteration 3: Workflow Intelligence ---
ASPECT_RATIOS = {
    "square": (768, 768),
    "portrait": (768, 1024),
    "cinematic": (1024, 768)
}

import os
import time

OUTPUT_DIR = r"c:\Users\jhk92\OneDrive\문서\GitHub\ai\Moltbot\output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def download_image(filename):
    print(f"    Downloading {filename}...")
    url = f"{BASE_URL}/view?filename={filename}&type=output"
    try:
        # Wait a bit for file to be ready on disk
        time.sleep(2)
        r = requests.get(url)
        r.raise_for_status()
        with open(os.path.join(OUTPUT_DIR, filename), 'wb') as f:
            f.write(r.content)
        print(f"    Saved: {filename}")
    except Exception as e:
        print(f"    Download Failed: {e}")

# --- Improvement Iteration 3: Workflow Intelligence ---
print(f"--- Starting MASTER BATCH (Iteration 3) ---")

for i in range(4):
    current_seed = random.randint(1, 1125899906842624)
    ar_name, (width, height) = random.choice(list(ASPECT_RATIOS.items()))
    
    pos, neg = get_enhanced_prompts(BASE_POSITIVE, BASE_NEGATIVE)
    
    workflow[POS_NODE_ID]["inputs"]["text"] = pos
    workflow[NEG_NODE_ID]["inputs"]["text"] = neg
    workflow[SAMPLER_NODE_ID]["inputs"]["seed"] = current_seed
    workflow[LATENT_NODE_ID]["inputs"]["width"] = width
    workflow[LATENT_NODE_ID]["inputs"]["height"] = height
    workflow[SAMPLER_NODE_ID]["inputs"]["steps"] = 30 # High quality for final pass
    
    prefix = f"iteration_3_{ar_name}_{current_seed}"
    workflow[SAVE_NODE_ID]["inputs"]["filename_prefix"] = prefix
    
    # --- Autonomous Prompt Logging ---
    prompt_log_path = os.path.join(OUTPUT_DIR, f"{prefix}_prompt.txt")
    try:
        with open(prompt_log_path, "w", encoding="utf-8") as pf:
            pf.write(f"--- POSITIVE PROMPT ---\n{pos}\n\n")
            pf.write(f"--- NEGATIVE PROMPT ---\n{neg}\n\n")
            pf.write(f"--- TECHNICAL DATA ---\nAR: {ar_name} | Seed: {current_seed} | Steps: 30")
        print(f"    Prompt Log Saved: {prefix}_prompt.txt")
    except Exception as e:
        print(f"    Failed to save prompt log: {e}")

    payload = {"prompt": workflow}
    
    print(f"[{i+1}/4] Mode: Master | AR: {ar_name} | Seed: {current_seed}...")
    try:
        res = requests.post(PROMPT_API, json=payload, timeout=30)
        res.raise_for_status()
        result = res.json()
        prompt_id = result.get('prompt_id')
        print(f"    Queued: {prompt_id}")
        
        # Note: In a real async environment, we'd poll /history.
        # Here we'll notify that download is available via download_results.py later
        # OR attempt immediate download (might fail if not processed yet).
        # We will assume the user has download_results.py for the real cleanup.
        
    except Exception as e:
        print(f"    ERROR: {e}")

from pod_manager import stop_pod

# --- Master Workflow Complete. ---
print("--- Master Workflow Complete. ---")

# --- Autonomous Shutdown Logic ---
if os.getenv("RUNPOD_API_KEY"):
    print("Initiating autonomous pod shutdown...")
    # Give a short buffer for the last request to be fully registered
    time.sleep(5)
    stop_pod()
else:
    print("NOTE: RUNPOD_API_KEY not found. Skipping automatic shutdown.")
    print("Please add RUNPOD_API_KEY to your .env file to enable this feature.")
