import streamlit as st
import json
from openai import OpenAI

# ------------------------------
# パスワード制限設定
# ------------------------------
ACCESS_PASSWORD = "forest2025"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 発達支援相談 AIエージェント")
    pwd = st.text_input("パスワードを入力してください", type="password")

    if st.button("ログイン"):
        if pwd == ACCESS_PASSWORD:
            st.session_state.authenticated = True
            st.success("ログイン成功しました")
            st.rerun()
        else:
            st.error("パスワードが違います")

    st.stop()

# ------------------------------
# OpenAI API (Secrets)
# ------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ------------------------------
# JSON 読み込み
# ------------------------------
with open("nd_kb_v2.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

# ------------------------------
# カテゴリスコアリング
# ------------------------------
def score_categories(text):
    scores = []
    for cat in kb["categories"]:
        score = 0
        for kw in cat.get("nlp_keywords", []):
            if kw in text:
                score += 1
        scores.append((cat["name"], score, cat))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores

# ------------------------------
# GPT 返答生成
# ------------------------------
def generate_response(conversation, category_name, user_input, support, rationale, source):
    previous_dialogue = "\n".join(
        [f"{'保護者' if sender=='user' else 'AI'}: {msg}" for msg, sender in conversation]
    )

    prompt = f"""
あなたは保護者に寄り添う発達支援アドバイザーです。
専門用語を避け、保護者が今日から実践できる方法を提案してください。
会話形式で丁寧に、500文字以内で回答してください。
最後に出典情報を別行として書いてください。

▼直前の会話:
{previous_dialogue}

▼今回の相談内容:
{user_input}

▼推定される特性:
{category_name}

▼支援の方向性:
{support}

▼根拠:
{rationale}

▼出典:
{source}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# ------------------------------
# Streamlit UI
# ------------------------------
st.set_page_config(page_title="発達支援相談 AIエージェント", layout="centered")

st.markdown("""
<h1 style='font-family:Zen Maru Gothic; text-align:center; color:#2d5a27;'>
🌱 発達支援相談 AIエージェント
</h1>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg, sender in st.session_state.messages:
    cls = "user-bubble" if sender=="user" else "chat-bubble"
    st.markdown(f'<div class="{cls}">{msg}</div>', unsafe_allow_html=True)

input_value = st.text_input("入力してください（気になる様子をご自由に）", key="chat_input")

col1, col2 = st.columns([1,5])
with col2:
    if st.button("送信"):
        if input_value.strip():
            st.session_state.messages.append((input_value, "user"))
            scores = score_categories(input_value)
            selected_name, _, selected_category = scores[0]

            supports = selected_category.get("recommended_supports", {})
            first = (supports.get("immediate") or supports.get("short_term_") or [{}])[0]

            support = first.get("description", "")
            rationale = first.get("rationale", "")
            source = first.get("source", "文部科学省 特別支援教育ガイドライン（2023）")

            answer = generate_response(
                st.session_state.messages, selected_name, input_value, support, rationale, source
            )

            st.session_state.messages.append((answer, "bot"))
            st.session_state.chat_input = ""  # 入力欄クリア
            st.rerun()

# Style
st.markdown("""
<style>
.chat-bubble {
    background:#ffffff; padding:15px; margin:10px 0;
    border-radius:12px; border:1px solid #d8cab8; font-size:18px;
}
.user-bubble {
    background:#dff4ff; padding:15px; margin:10px 0;
    text-align:right; border-radius:12px; border:1px solid #96c7e6; font-size:18px;
}
</style>
""", unsafe_allow_html=True)
