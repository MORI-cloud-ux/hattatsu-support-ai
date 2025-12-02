import streamlit as st
import json
from openai import OpenAI
import uuid

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
# カテゴリ判定
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
    history_text = "\n".join(
        [f"保護者: {m[0]}" if m[1] == "user" else f"AI: {m[0]}" for m in history[-4:]]
    )

    prompt = f"""
あなたは保護者支援専門のやさしい発達支援カウンセラーです。
専門用語を使わず、今日から家庭でできる具体的な工夫を、会話のように伝えてください。
500文字前後、自然な文章、共感の姿勢で。

【これまでの相談履歴】
{history_text}

【今回の相談】
{user_input}

【推定される発達特性】
{category_name}

【支援の方向性】
{support}

【背景の理解】
{rationale}

※ 出典は文末に「📚 出典：」の形で記載してください。
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


# ==============================
# チャット履歴表示
# ==============================
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg, sender in st.session_state.messages:
    bubble = "user-bubble" if sender == "user" else "bot-bubble"
    st.markdown(f'<div class="{bubble}">{msg}</div>', unsafe_allow_html=True)


# ==============================
# 入力欄管理（UUID方式でクリア）
# ==============================
if "input_key" not in st.session_state:
    st.session_state.input_key = str(uuid.uuid4())

user_input = st.text_area(
    "入力してください：",
    key=st.session_state.input_key,
    height=160,
    placeholder="気になる様子を自由にお書きください（自動改行・制限なし）",
)

# ==============================
# 送信
# ==============================
if st.button("送信", use_container_width=True):
    if user_input.strip():
        st.session_state.messages.append((user_input, "user"))

        scores = score_categories(user_input)
        selected_name, _, selected_category = scores[0]

        supports = selected_category.get("recommended_supports", {})
        first = (supports.get("immediate") or supports.get("short_term") or supports.get("long_term") or [{}])[0]

        support = first.get("description", "家庭や学校での環境調整が有効とされています。")
        rationale = first.get("rationale", "行動の背景には特性理解が重要とされています。")
        source = first.get("source", "文部科学省 特別支援教育ガイドライン（2023）")

        answer = generate_response(st.session_state.messages, selected_name, user_input, support, rationale, source)
        full_answer = f"{answer}\n\n📚 出典：{source}"

        st.session_state.messages.append((full_answer, "bot"))

        # 🎯 入力欄のキーを更新 → 再生成 → 自動クリア
        st.session_state.input_key = str(uuid.uuid4())
        st.rerun()
