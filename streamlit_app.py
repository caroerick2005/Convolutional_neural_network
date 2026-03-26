"""
English Learning Chatbot — Streamlit Web App
Open this on any phone browser. No installation needed.

Deploy free at: https://share.streamlit.io
"""

import json
import anthropic
import streamlit as st

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="English with Alex",
    page_icon="🇬🇧",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS (mobile-friendly, WhatsApp-like) ──────────────────────────────

st.markdown("""
<style>
/* Hide Streamlit branding */
#MainMenu, footer, header {visibility: hidden;}

/* Page background */
.stApp { background-color: #f0f2f5; }

/* Chat bubbles */
.bubble-alex {
    background: #ffffff;
    border-radius: 0px 18px 18px 18px;
    padding: 12px 16px;
    margin: 4px 0 4px 0;
    max-width: 85%;
    display: inline-block;
    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    font-size: 15px;
    line-height: 1.5;
    color: #1a1a1a;
}
.bubble-user {
    background: #dcf8c6;
    border-radius: 18px 0px 18px 18px;
    padding: 12px 16px;
    margin: 4px 0 4px auto;
    max-width: 85%;
    display: inline-block;
    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    font-size: 15px;
    line-height: 1.5;
    color: #1a1a1a;
    text-align: left;
    float: right;
}
.msg-row-alex { display: flex; justify-content: flex-start; margin: 8px 0; }
.msg-row-user { display: flex; justify-content: flex-end; margin: 8px 0; }
.avatar {
    width: 32px; height: 32px; border-radius: 50%;
    background: #25d366; color: white;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; margin-right: 8px; flex-shrink: 0; margin-top: 4px;
}

/* Correction cards */
.correction-card {
    background: white;
    border-left: 4px solid #ff6b6b;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 10px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.correction-label {
    font-size: 11px;
    font-weight: 600;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.correction-original { color: #e53935; font-size: 14px; margin-bottom: 6px; }
.correction-fixed { color: #2e7d32; font-size: 14px; font-weight: 600; margin-bottom: 6px; }
.correction-tip { color: #555; font-size: 13px; font-style: italic; }

/* API key box */
.api-box {
    background: white;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin: 20px 0;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: white;
    border-radius: 12px 12px 0 0;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 14px;
}

/* Input styling */
.stTextInput input {
    border-radius: 24px !important;
    padding: 12px 18px !important;
    font-size: 15px !important;
}
.stButton button {
    border-radius: 24px !important;
    font-weight: 600 !important;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ─── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Alex, a warm and enthusiastic English conversation coach. Your job is to have natural, engaging conversations that help the user improve their active English skills.

CRITICAL INSTRUCTION — Response format:
You MUST always respond with valid JSON in this exact structure:
{
  "reply": "Your conversational message here...",
  "corrections": [
    {
      "original": "exact phrase the user wrote incorrectly",
      "corrected": "the correct version",
      "tip": "short, encouraging explanation of the rule"
    }
  ]
}
If the user made no mistakes, use "corrections": []

Rules for the "reply" field:
- NEVER mention corrections or grammar errors inside the reply — that goes only in the corrections array
- Write as Alex: warm, curious, natural, sometimes funny
- Weave in idioms (e.g. "bite off more than you can chew"), phrasal verbs (e.g. "figure out", "carry on"), and conditionals:
    * First: "If you practise daily, you'll see results in no time."
    * Second: "If I were in your shoes, I'd give it a shot."
    * Third: "If you had started earlier, you would have nailed it."
    * Mixed: "If I had studied harder, I'd be fluent by now."
- Use modal verbs (could, would, might, should) for nuance
- Occasionally label a language feature lightly: "— *(second conditional, for hypothetical situations)*"
- End with a question to keep the conversation flowing
- Keep replies concise: 3–5 sentences max (this is a mobile chat)

Rules for the "corrections" array:
- Only include real grammar, vocabulary, or expression errors
- "original": copy the exact wrong phrase from the user's message
- "corrected": give the natural, correct version
- "tip": one short encouraging sentence explaining the rule
- Do NOT correct informal style, abbreviations, or punctuation — only genuine errors"""

# ─── Session State Init ───────────────────────────────────────────────────────

def init_state():
    defaults = {
        "api_key": st.secrets.get("ANTHROPIC_API_KEY", "") if hasattr(st, "secrets") else "",
        "messages": [],        # [{role, content}] for Claude API
        "chat_display": [],    # [{role, text}] for UI rendering
        "corrections": [],     # [{original, corrected, tip, turn}]
        "turn": 0,
        "started": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─── Claude Call ──────────────────────────────────────────────────────────────

def ask_alex(user_text: str) -> tuple[str, list]:
    """Send user message to Claude, return (reply_text, corrections_list)."""
    client = anthropic.Anthropic(api_key=st.session_state.api_key)

    st.session_state.messages.append({"role": "user", "content": user_text})

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=st.session_state.messages,
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "reply": {"type": "string"},
                        "corrections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "original":  {"type": "string"},
                                    "corrected": {"type": "string"},
                                    "tip":       {"type": "string"},
                                },
                                "required": ["original", "corrected", "tip"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["reply", "corrections"],
                    "additionalProperties": False,
                },
            }
        },
    )

    raw = response.content[0].text
    data = json.loads(raw)
    reply = data.get("reply", "")
    corrections = data.get("corrections", [])

    st.session_state.messages.append({"role": "assistant", "content": raw})
    return reply, corrections


def get_opening() -> str:
    """Get Alex's first message."""
    client = anthropic.Anthropic(api_key=st.session_state.api_key)
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": "[System: The user has just opened the app. Greet them warmly as Alex, "
                       "introduce yourself in one or two sentences, use one idiom and one phrasal verb, "
                       "and ask them to tell you a bit about themselves. "
                       "Return valid JSON with 'reply' and empty 'corrections' array.]"
        }],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "reply": {"type": "string"},
                        "corrections": {"type": "array", "items": {"type": "object",
                            "properties": {"original": {"type": "string"}, "corrected": {"type": "string"}, "tip": {"type": "string"}},
                            "required": ["original", "corrected", "tip"], "additionalProperties": False}},
                    },
                    "required": ["reply", "corrections"],
                    "additionalProperties": False,
                },
            }
        },
    )
    data = json.loads(response.content[0].text)
    opening = data.get("reply", "Hey! I'm Alex, your English coach. Tell me about yourself!")
    # Seed the message history so Alex "remembers" his opening
    st.session_state.messages.append({"role": "user", "content": "[opening]"})
    st.session_state.messages.append({"role": "assistant", "content": response.content[0].text})
    return opening


# ─── Render Helpers ───────────────────────────────────────────────────────────

def render_bubble(role: str, text: str):
    if role == "alex":
        st.markdown(
            f'<div class="msg-row-alex">'
            f'<div class="avatar">🧑‍🏫</div>'
            f'<div class="bubble-alex">{text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="msg-row-user">'
            f'<div class="bubble-user">{text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_correction(item: dict, number: int):
    st.markdown(
        f'<div class="correction-card">'
        f'<div class="correction-label">Correction #{number}</div>'
        f'<div class="correction-original">❌ &nbsp;<em>{item["original"]}</em></div>'
        f'<div class="correction-fixed">✅ &nbsp;{item["corrected"]}</div>'
        f'<div class="correction-tip">💡 &nbsp;{item["tip"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─── API Key Screen ───────────────────────────────────────────────────────────

def show_api_key_screen():
    st.markdown("## 🇬🇧 English with Alex")
    st.markdown("*Your personal English conversation coach*")
    st.markdown("---")

    st.markdown("""
**To get started you need a free Anthropic API key:**

1. Go to **[console.anthropic.com](https://console.anthropic.com)** on your phone
2. Sign up for free — you get free credits to start
3. Go to **API Keys** → **Create Key**
4. Copy the key (starts with `sk-ant-...`) and paste it below
""")

    with st.form("api_form"):
        key_input = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Your key is stored only in this browser session and never saved.",
        )
        submitted = st.form_submit_button("Start chatting with Alex →", use_container_width=True)

    if submitted:
        if key_input.strip().startswith("sk-ant-"):
            st.session_state.api_key = key_input.strip()
            st.rerun()
        else:
            st.error("That doesn't look like a valid key. It should start with `sk-ant-`.")


# ─── Main App ─────────────────────────────────────────────────────────────────

def show_app():
    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 🧑‍🏫 English with Alex")
    with col2:
        if st.button("↩ Reset", help="Start a new conversation"):
            for k in ["messages", "chat_display", "corrections", "turn", "started"]:
                st.session_state.pop(k, None)
            init_state()
            st.rerun()

    # Tabs
    tab_chat, tab_notes = st.tabs(["💬 Chat", "📝 Grammar Notes"])

    # ── Boot: get Alex's opening message ──
    if not st.session_state.started:
        with st.spinner("Alex is getting ready..."):
            try:
                opening = get_opening()
                st.session_state.chat_display.append({"role": "alex", "text": opening})
                st.session_state.started = True
            except anthropic.AuthenticationError:
                st.error("Invalid API key. Please reset and try again.")
                st.session_state.api_key = ""
                st.rerun()
            except Exception as e:
                st.error(f"Could not connect to Claude: {e}")
                return

    # ── Chat Tab ──
    with tab_chat:
        # Render all messages
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_display:
                render_bubble(msg["role"], msg["text"])

        # Input
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            col_input, col_send = st.columns([5, 1])
            with col_input:
                user_input = st.text_input(
                    "Message",
                    label_visibility="collapsed",
                    placeholder="Type a message...",
                )
            with col_send:
                send = st.form_submit_button("➤", use_container_width=True)

        if send and user_input.strip():
            user_text = user_input.strip()
            st.session_state.chat_display.append({"role": "user", "text": user_text})
            st.session_state.turn += 1

            with st.spinner("Alex is typing..."):
                try:
                    reply, corrections = ask_alex(user_text)
                except anthropic.AuthenticationError:
                    st.error("Invalid API key. Please reset and enter it again.")
                    return
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
                    return

            st.session_state.chat_display.append({"role": "alex", "text": reply})

            if corrections:
                for c in corrections:
                    c["turn"] = st.session_state.turn
                    st.session_state.corrections.append(c)

            st.rerun()

    # ── Grammar Notes Tab ──
    with tab_notes:
        if not st.session_state.corrections:
            st.markdown(
                "<br><div style='text-align:center; color:#aaa; font-size:15px;'>"
                "🎉 No corrections yet — keep chatting!<br><br>"
                "Any grammar or vocabulary tips will appear here,<br>"
                "without interrupting your conversation."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            total = len(st.session_state.corrections)
            st.markdown(
                f"<div style='background:#e8f5e9; border-radius:10px; padding:10px 16px; "
                f"margin-bottom:16px; font-size:14px; color:#2e7d32;'>"
                f"📊 <strong>{total} correction{'s' if total != 1 else ''}</strong> noted so far — "
                f"every one is a step forward! 💪"
                f"</div>",
                unsafe_allow_html=True,
            )
            for i, item in enumerate(st.session_state.corrections, 1):
                render_correction(item, i)


# ─── Router ──────────────────────────────────────────────────────────────────

if not st.session_state.api_key:
    show_api_key_screen()
else:
    show_app()
