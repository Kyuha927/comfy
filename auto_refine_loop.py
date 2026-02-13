import time
import random
from serverless_hidream import generate_serverless_image, wait_and_download
from vision_feedback import analyze_image

MAX_RETRIES = 5
QUALITY_THRESHOLD = 8

def run_autonomous_loop():
    print(f"🚀 Starting Autonomous Feedback Loop (Threshold: {QUALITY_THRESHOLD}/10)")
    
    # User-Requested Dieselpunk Prompt
    pos = (
        "(masterpiece, best quality), 16-bit pixel art, character sprite, "
        "white background, dieselpunk villain, large muscular male, "
        "tattered black formal suit covered in dust and oil, rusty mechanical armor, "
        "worn-out metal, exposed wires, flickering dim amber eye sensor, "
        "industrial machinery parts on chest, massive heavy hydraulic arm cannon, "
        "retro game style, gritty texture, detailed weathering"
    )
    neg = "low quality, blurry, 3d, realistic, photo, bad anatomy"

    resolutions = [1024, 768, 512]
    
    for i in range(1, MAX_RETRIES + 1):
        seed = random.randint(1, 9999999999)
        # Cycle through resolutions
        res = resolutions[(i-1) % len(resolutions)]
        
        print(f"\n🔄 Attempt {i}/{MAX_RETRIES} (Seed: {seed}, Res: {res}x{res})")
        
        # 1. Generate Image
        job_id = generate_serverless_image(pos, neg, seed, width=res, height=res)
        if not job_id:
            print("❌ Failed to start job. Retrying...")
            continue
            
        saved_files = wait_and_download(job_id, seed)
        if not saved_files:
            print("❌ No files generated. Retrying...")
            continue
            
        latest_image = saved_files[0]
        
        # 2. Analyze Image
        prompt = (
            "Analyze this pixel art character image. "
            "1. Is the resolution high quality and clear (1024x1024 level) or blurry/broken? "
            "2. Does it accurately depict a 'dieselpunk villain'? "
            "3. Rate the overall quality from 1 to 10. "
            "IMPORTANT: You MUST end your response with exactly: 'Score: X/10' where X is the number."
        )
        
        print(f"👀 Analyzing {latest_image}...")
        score, feedback = analyze_image(latest_image, prompt)
        
        print(f"📊 Quality Score: {score}/10")
        
        if score >= QUALITY_THRESHOLD:
            print(f"\n✨ SUCCESS! High quality image generated: {latest_image}")
            print(f"📝 AI Feedback: {feedback}")
            return latest_image
        else:
            print(f"⚠️ Quality too low ({score}/{QUALITY_THRESHOLD}). Retrying...")

    print("\n❌ Max retries reached without meeting quality threshold.")
    return None

if __name__ == "__main__":
    run_autonomous_loop()
