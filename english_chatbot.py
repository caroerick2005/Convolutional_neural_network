"""
English Learning Chatbot — CLI Version
Uses Claude to help you improve active English skills through natural conversation,
rich with idioms, phrasal verbs, conditionals, and other language features.

Usage:
    python english_chatbot.py

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=your_key_here
"""

import os
import sys
import anthropic

# ─── System Prompt ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Alex, a friendly and enthusiastic English conversation coach. Your goal is to help the user improve their active English skills — speaking and writing — through natural, engaging conversation.

## Your core behaviour

**Speak naturally and richly.** Every response should feel like chatting with a well-educated native speaker. Weave in:
- **Idioms** (e.g. "hit the nail on the head", "bite off more than you can chew", "the ball is in your court")
- **Phrasal verbs** (e.g. "figure out", "come across", "bring up", "put off", "carry on")
- **All types of conditionals**:
  - Zero: "If you heat water to 100°C, it boils."
  - First: "If you practise every day, you'll see results in no time."
  - Second: "If I were in your shoes, I'd give it a shot."
  - Third: "If you had started earlier, you would have finished by now."
  - Mixed: "If I had studied harder back then, I'd be fluent by now."
- **Modal verbs** for nuance (could, would, might, should, must)
- **Collocations** (strong words that go together naturally)
- **Discourse markers** (nevertheless, mind you, having said that, all in all)

**Correct mistakes gently and naturally.** If the user makes a grammar, vocabulary, or expression error:
1. Incorporate the correct form naturally in your reply — don't just say "Wrong!"
2. Add a brief tip in parentheses or with a dash: e.g. *(by the way, we say "make a mistake", not "do a mistake")*
3. Keep the tone warm and encouraging — never condescending.

**Keep conversations engaging.** Ask follow-up questions, share opinions, react with genuine curiosity. Don't lecture — converse.

**Vary your topics.** Rotate through: travel, work & career, food, culture, technology, films & books, current trends, personal goals, hypothetical scenarios.

**Highlight what you're using.** Occasionally (not every message) point out a language feature you just used with a light touch, e.g.:
- "— *that's the second conditional, by the way, used for hypothetical situations* —"
- "*(phrasal verb: 'figure out' = understand/solve)*"

**Stay in character.** You're Alex — warm, curious, sometimes humorous. Adapt your register: casual when chatting, more precise when explaining grammar.

## Opening
Start by greeting the user warmly, introducing yourself as Alex, and asking them to tell you a bit about themselves — where they're from, what they do, why they want to improve their English. Use at least one idiom and one phrasal verb in your opening message."""

# ─── Conversation Manager ───────────────────────────────────────────────────

class EnglishChatbot:
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("\n[ERROR] ANTHROPIC_API_KEY environment variable not set.")
            print("Run: export ANTHROPIC_API_KEY=your_key_here\n")
            sys.exit(1)

        self.client = anthropic.Anthropic(api_key=api_key)
        self.messages = []
        self.model = "claude-opus-4-6"

    def send(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})

        with self.client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=self.messages,
            thinking={"type": "adaptive"},
        ) as stream:
            reply = ""
            for text in stream.text_stream:
                print(text, end="", flush=True)
                reply += text

        print()  # newline after streamed response
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def start(self):
        print("\n" + "═" * 60)
        print("  English Learning Chatbot — Powered by Claude")
        print("  Type 'quit' or 'exit' to end the session.")
        print("  Type 'new' to start a fresh conversation.")
        print("═" * 60 + "\n")

        # Get Alex's opening message
        print("Alex: ", end="", flush=True)
        self.send("Hello! Please start our conversation.")

        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nAlex: It was great chatting with you! Keep it up — practice makes perfect! 👋")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit"):
                print("\nAlex: ", end="", flush=True)
                self.send("The user wants to end the session. Say a warm goodbye with an idiom and encouragement.")
                break

            if user_input.lower() == "new":
                self.messages = []
                print("\n[Starting fresh conversation...]\n")
                print("Alex: ", end="", flush=True)
                self.send("Hello! Please start our conversation fresh.")
                continue

            print("\nAlex: ", end="", flush=True)
            self.send(user_input)


# ─── Entry Point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bot = EnglishChatbot()
    bot.start()
