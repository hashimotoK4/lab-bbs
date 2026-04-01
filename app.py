import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json # これを追加

# Firebaseの初期化
if not firebase_admin._apps:
    # SecretsからJSONの塊を取り出す
    raw_json = st.secrets["firebase"]["json_data"]
    
    # 文字列を辞書形式に変換
    firebase_info = json.loads(raw_json)
    
    # 秘密鍵の改行コードだけは念のため修正
    firebase_info["private_key"] = firebase_info["private_key"].replace("\\n", "\n")
    
    cred = credentials.Certificate(firebase_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 画面の構成 ---
st.set_page_config(page_title="研究室掲示板", layout="centered")
st.title("🚀 研究室 掲示板")

# 入力フォーム
with st.form("my_form", clear_on_submit=True):
    st.subheader("新しい投稿")
    user_name = st.text_input("名前", placeholder="界翔")
    message = st.text_area("メッセージ", placeholder="ここに内容を入力...")
    submit_button = st.form_submit_button("送信する")

    if submit_button and user_name and message:
        # Firebase (Firestore) にデータを保存
        doc_ref = db.collection("posts").document()
        doc_ref.set({
            "name": user_name,
            "content": message,
            "timestamp": firestore.SERVER_TIMESTAMP # サーバー側の時刻を記録
        })
        st.success("投稿が完了しました！")

st.divider()

# --- 投稿の表示 ---
st.subheader("掲示板ログ")

# データを新しい順に取得
posts_ref = db.collection("posts").order_by("timestamp", direction=firestore.Query.DESCENDING)
posts = posts_ref.stream()

for post in posts:
    p = post.to_dict()
    # 投稿をカード形式で表示
    with st.container():
        st.markdown(f"**{p.get('name')}**")
        st.write(p.get('content'))
        # 時刻表示（Noneチェック付き）
        ts = p.get('timestamp')
        if ts:
            st.caption(f"📅 {ts.strftime('%Y-%m-%d %H:%M')}")
        st.divider()