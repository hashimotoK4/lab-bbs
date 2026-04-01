import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime

# Firebaseの初期化（前回の設定を維持）
if not firebase_admin._apps:
    raw_json = st.secrets["firebase"]["json_data"]
    firebase_info = json.loads(raw_json)
    firebase_info["private_key"] = firebase_info["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(firebase_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="研究室掲示板 Pro", layout="centered")
st.title("🚀 研究室 掲示板")

# --- 投稿フォーム ---
with st.form("main_form", clear_on_submit=True):
    user_name = st.text_input("名前", placeholder="界翔")
    message = st.text_area("メッセージ")
    if st.form_submit_button("投稿する") and user_name and message:
        db.collection("posts").add({
            "name": user_name,
            "content": message,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "likes": 0,
            "replies": []
        })
        st.rerun()

st.divider()

# --- 投稿の表示 ---
posts = db.collection("posts").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()

for post in posts:
    p_id = post.id
    p = post.to_dict()
    
    with st.expander(f"💬 {p.get('name')} : {p.get('content')[:20]}...", expanded=True):
        st.write(p.get('content'))
        
        # --- いいね機能 ---
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button(f"❤️ {p.get('likes', 0)}", key=f"like_{p_id}"):
                db.collection("posts").document(p_id).update({"likes": firestore.Increment(1)})
                st.rerun()
        
        # --- リプライ表示 ---
        replies = p.get('replies', [])
        for r in replies:
            st.markdown(f"┗ **{r['name']}**: {r['content']}")
        
        # --- リプライ入力 ---
        with st.form(key=f"reply_form_{p_id}", clear_on_submit=True):
            r_name = st.text_input("名前", key=f"rname_{p_id}", value="界翔")
            r_msg = st.text_input("返信内容", key=f"rmsg_{p_id}")
            if st.form_submit_button("返信"):
                if r_name and r_msg:
                    new_reply = {"name": r_name, "content": r_msg, "at": datetime.now().isoformat()}
                    db.collection("posts").document(p_id).update({
                        "replies": firestore.ArrayUnion([new_reply])
                    })
                    st.rerun()