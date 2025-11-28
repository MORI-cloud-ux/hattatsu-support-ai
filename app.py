import streamlit as st
import json
from openai import OpenAI

# ==============================
# Streamlit設定
# ==============================
st.set_page_config(page_title="発達支援相談AIエージェント", layout="centered")

# ==============================
# パスワード認証
# ==============================
PASSWORD = "forest2025"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align:center;'>🌿 発達支援相談AIエージェント</h2>", unsafe_allow_html=True)
    pwd = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if pwd == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# ==============================
# OpenAI設定（Secrets推奨）
# ==============================
API_KEY = st.secrets.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=API_KEY)

# ==============================
# JSON読み込み
# ==============================
with open("nd_kb_v2.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

# ==============================
# スコアリング
# ==============================
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

# ==============================
# GPT回答生成
# ==============================
def generate_response(history, category_name, user_input, support, rationale, source):
    conversation_log = "\n".join(
        [f"保護者: {m[0]}" if m[1] == "user" else f"AI: {m[0]}" for m in history[-6:]]
    )

    prompt = f"""
あなたは保護者支援専門の心理士兼特別支援教育の専門家です。
抽象論ではなく、家庭で今日から実践できる温かい助言を伝えてください。

【相談履歴】
{conversation_log}

【今回の相談内容】
{user_input}

【推定される特性】{category_name}

500文字以内で下記構造で回答：
- 共感
- 行動背景のやさしい説明
- 家庭でできる工夫（3つ箇条書き）
- 学校との連携方法（1つ）
- 避けたい対応（1つ）
- 温かい励ましの一言

出典は本文には含めず、最後に別記してください
出典：{source}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# ==============================
# UIスタイル
# ==============================
st.markdown("""
<style>
body { background-color: #fff7ed; }
.chat-bubble { background: #ffffff; padding: 15px; margin: 10px 0;
               border-radius: 12px; border: 1px solid #e5c7a5; }
.user-bubble { background: #dff4ff; padding: 15px; margin: 10px 0;
               text-align:right; border-radius:12px; border:1px solid #96c7e6; }
.title { font-size:28px; font-family: 'Zen Maru Gothic'; text-align:center; font-weight:600; color:#4b6043; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🌿 発達支援相談AIエージェント</div>', unsafe_allow_html=True)
st.write("気になる様子を自由に書いてください。")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg, sender in st.session_state.messages:
    cls = "user-bubble" if sender == "user" else "chat-bubble"
    st.markdown(f'<div class="{cls}">{msg}</div>', unsafe_allow_html=True)

# 入力欄（リセットは自動で行われる）
chat_input = st.text_input("入力してください：", key="chat_input")

if st.button("送信"):
    if chat_input.strip():
        st.session_state.messages.append((chat_input, "user"))

        scores = score_categories(chat_input)
        name, score, selected_category = scores[0]

        supports = selected_category.get("recommended_supports", {})
        first = (supports.get("immediate") or supports.get("short_term") or supports.get("long_term") or [{}])[0]

        support = first.get("description", "家庭での環境調整が役に立つ場合があります。")
        rationale = first.get("rationale", "行動背景の理解が重要とされています。")
        source = first.get("source", "文部科学省 特別支援教育ガイドライン（2023）")

        answer = generate_response(st.session_state.messages, name, chat_input, support, rationale, source)
        st.session_state.messages.append((answer, "bot"))

        st.rerun()  # 入力欄が自動的に空になる
