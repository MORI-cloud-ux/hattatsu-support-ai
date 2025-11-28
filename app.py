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
# OpenAI設定
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
        score = sum(1 for kw in cat.get("nlp_keywords", []) if kw in text)
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
あなたは保護者支援専門のあたたかい発達支援カウンセラーです。
専門用語を使わず、今日から家庭でできる小さな実践を、優しく具体的に会話のように説明してください。
500文字程度で自然な文章にしてください。

【これまでの相談履歴】
{conversation_log}

【今回の相談】
{user_input}

【推定される特性】
{category_name}

【支援方針】
{support}

【背景理解】
{rationale}

※ 出典は文末に「📚 出典：{source}」として必ず添えてください。
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# ==============================
# UI表示準備
# ==============================
st.markdown(
    "<h2 style='text-align:center; font-family:Zen Maru Gothic;'>🌿 発達支援相談AIエージェント</h2>",
    unsafe_allow_html=True
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg, sender in st.session_state.messages:
    cls = "user-bubble" if sender == "user" else "chat-bubble"
    st.markdown(f'<div class="{cls}">{msg}</div>', unsafe_allow_html=True)

# テキスト入力管理
if "chat_input" not in st.session_state:
    st.session_state.chat_input = ""

user_input = st.text_input("入力してください：", key="chat_input")

# ==============================
# 送信処理
# ==============================
if st.button("送信"):
    if user_input.strip():
        st.session_state.messages.append((user_input, "user"))

        scores = score_categories(user_input)
        selected_name, _, selected_category = scores[0]

        supports = selected_category.get("recommended_supports", {})
        first = (supports.get("immediate") or supports.get("short_term") or supports.get("long_term") or [{}])[0]

        support = first.get("description", "家庭や学校での環境調整が有効とされています。")
        rationale = first.get("rationale", "行動の背景には発達理解が重要とされています。")
        source = first.get("source", "文部科学省 特別支援教育ガイドライン（2023）")

        answer = generate_response(
            st.session_state.messages, selected_name, user_input, support, rationale, source
        )

        st.session_state.messages.append((answer, "bot"))

        # 入力欄をリセット
        del st.session_state["chat_input"]
        st.rerun()

