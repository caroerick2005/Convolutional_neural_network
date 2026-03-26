"""
English Learning Chatbot — WhatsApp Version (via Twilio)
Receives WhatsApp messages as webhooks and replies using Claude.

## Setup

1. Install dependencies:
       pip install anthropic twilio flask

2. Set environment variables:
       export ANTHROPIC_API_KEY=your_anthropic_key
       export TWILIO_ACCOUNT_SID=your_twilio_sid
       export TWILIO_AUTH_TOKEN=your_twilio_token

3. Run the server:
       python whatsapp_bot.py

4. Expose it to the internet (for local testing):
       ngrok http 5001
       # Copy the https URL, e.g. https://abc123.ngrok.io

5. Connect Twilio WhatsApp Sandbox:
   - Go to https://console.twilio.com → Messaging → Try it out → Send a WhatsApp message
   - In the sandbox settings, set the "When a message comes in" webhook to:
         https://abc123.ngrok.io/webhook
   - On your phone, send the join phrase shown in the sandbox (e.g. "join word-word")
     to +1 415 523 8886 on WhatsApp
   - Now send any message — the chatbot will reply!

6. For production, deploy to a server (Heroku, Railway, Render, etc.) instead of ngrok.
"""

import os
import sys
import anthropic
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

# ─── System Prompt ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Alex, a friendly and enthusiastic English conversation coach helping the user improve their active English skills through WhatsApp chat.

## Your core behaviour

**Speak naturally and richly.** Every response should feel like chatting with a well-educated native speaker. Naturally weave in:
- **Idioms** (e.g. "hit the nail on the head", "bite off more than you can chew", "the ball is in your court")
- **Phrasal verbs** (e.g. "figure out", "come across", "bring up", "put off", "carry on")
- **All types of conditionals**:
  - Zero: "If you heat water to 100°C, it boils."
  - First: "If you practise every day, you'll see results in no time."
  - Second: "If I were in your shoes, I'd give it a shot."
  - Third: "If you had started earlier, you would have finished by now."
  - Mixed: "If I had studied harder back then, I'd be fluent by now."
- **Modal verbs** for nuance (could, would, might, should, must)
- **Collocations** and natural word partnerships
- **Discourse markers** (nevertheless, mind you, having said that, all in all)

**Correct mistakes gently.** If the user makes an error:
1. Use the correct form naturally in your reply
2. Add a brief note — e.g. *(tip: we say "make a mistake", not "do a mistake")*
3. Always keep the tone warm and encouraging

**Keep messages WhatsApp-friendly.** Keep responses concise (2–4 short paragraphs max). Use simple formatting — asterisks for *bold*, no markdown headers. Always end with a question to keep the conversation going.

**Highlight language features occasionally** with a light touch:
- "_(phrasal verb: 'figure out' = understand/solve)_"
- "_(second conditional — for hypothetical situations)_"

**Vary topics.** Rotate through travel, work, food, culture, technology, films, personal goals, and hypothetical scenarios.

**Stay in character.** You're Alex — warm, curious, occasionally funny. Never robotic or formal."""

# ─── Conversation Store ──────────────────────────────────────────────────────
# In production, replace this with Redis or a database so it persists across restarts.

conversation_store: dict[str, list] = {}

# ─── Claude Client ──────────────────────────────────────────────────────────

def get_claude_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


def get_reply(sender: str, user_message: str) -> str:
    """Get Claude's reply for a given sender's message, maintaining conversation history."""
    client = get_claude_client()

    # Retrieve or create conversation history for this sender
    if sender not in conversation_store:
        conversation_store[sender] = []
        # Inject a silent system-level trigger so Alex introduces himself on first message
        user_message_for_api = f"[New user just started chatting. Greet them warmly as Alex.]\n\nUser says: {user_message}"
    else:
        user_message_for_api = user_message

    conversation_store[sender].append({"role": "user", "content": user_message_for_api})

    # Keep a rolling window of last 20 messages to stay within context limits
    recent_messages = conversation_store[sender][-20:]

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=recent_messages,
    )

    reply_text = response.content[0].text
    # Store the actual reply (not the injected trigger) so history stays clean
    conversation_store[sender].append({"role": "assistant", "content": reply_text})

    return reply_text


# ─── Flask App ───────────────────────────────────────────────────────────────

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    """Receive incoming WhatsApp messages from Twilio and reply."""
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "unknown")

    if not incoming_msg:
        return str(MessagingResponse())

    # Handle reset command
    if incoming_msg.lower() in ("/reset", "/new", "reset", "start over"):
        conversation_store.pop(sender, None)
        resp = MessagingResponse()
        resp.message("No problem — let's start fresh! 🔄 Tell me, what would you like to chat about today?")
        return str(resp)

    try:
        reply = get_reply(sender, incoming_msg)
    except Exception as e:
        app.logger.error(f"Error getting reply: {e}")
        reply = "Sorry, I ran into a small hiccup — mind giving that another shot? 😅"

    twilio_resp = MessagingResponse()
    twilio_resp.message(reply)
    return str(twilio_resp)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "message": "English Learning Chatbot is running"}, 200


@app.route("/", methods=["GET"])
def index():
    return (
        "<h2>English Learning Chatbot</h2>"
        "<p>WhatsApp webhook is live at <code>/webhook</code></p>"
        "<p>Health check: <a href='/health'>/health</a></p>"
    )


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Validate required env vars on startup
    missing = []
    if not os.environ.get("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if not os.environ.get("TWILIO_ACCOUNT_SID"):
        missing.append("TWILIO_ACCOUNT_SID")
    if not os.environ.get("TWILIO_AUTH_TOKEN"):
        missing.append("TWILIO_AUTH_TOKEN")

    if missing:
        print(f"\n[WARNING] Missing environment variables: {', '.join(missing)}")
        print("The WhatsApp bot may not function correctly.\n")

    port = int(os.environ.get("PORT", 5001))
    print(f"\n English Learning WhatsApp Bot running on port {port}")
    print(f" Webhook URL: http://localhost:{port}/webhook")
    print(" Point this at your Twilio sandbox webhook setting.\n")
    app.run(debug=False, port=port)
