import os
import time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from agent import MoltbotAgent

# Load environment variables
load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

# Initialize Slack App
app = App(token=SLACK_BOT_TOKEN)

# Initialize Moltbot Agent (default to auto-routing)
agent = MoltbotAgent(provider="google") # Using Google as default for Slack speed

@app.event("app_mention")
def handle_app_mentions(event, say):
    user_id = event["user"]
    text = event["text"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    
    # Clean mention from text
    # <@U12345> Hello -> Hello
    import re
    prompt = re.sub(r"<@U[A-Z0-9]+>", "", text).strip()
    
    print(f" [Slack] User {user_id} requested: {prompt}")
    
    if not prompt:
        say("네, 몰트봇입니다! 무엇을 도와드릴까요?", thread_ts=thread_ts)
        return

    # Thinking indicator (Slack doesn't have a native one for Socket Mode, so we just start)
    try:
        # Get response from Moltbot
        full_response = ""
        for part in agent.get_response(prompt):
            if part:
                full_response += part + "\n"
        
        if full_response.strip():
            say(full_response.strip(), thread_ts=thread_ts)
        else:
            say("죄송합니다. 응답을 생성하지 못했습니다.", thread_ts=thread_ts)
            
    except Exception as e:
        print(f" [Slack] Error: {e}")
        say(f"❌ 오류 발생: {str(e)}", thread_ts=thread_ts)

if __name__ == "__main__":
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        print("❌ Error: SLACK_BOT_TOKEN or SLACK_APP_TOKEN missing in .env")
        print("Please set them up at api.slack.com/apps")
    else:
        print("⚡ Moltbot Slack Agent is starting...")
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
