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

st.set_page_config(page_title="研究室掲示板", layout="centered")
st.title("🚀 研究室 掲示板")

# --- 投稿フォーム ---
with st.form("main_form", clear_on_submit=True):
    user_name = st.text_input("名前", placeholder="匿名希望")
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
    replies = p.get('replies', [])

    with st.container(border=True):
        st.markdown(f"### 👤 {p.get('name')}")
        st.write(p.get('content'))
        
       
        if st.button(f"❤️ {p.get('likes', 0)}", key=f"like_{p_id}"):
                db.collection("posts").document(p_id).update({"likes": firestore.Increment(1)})
                st.rerun()
        
        # --- リプライ表示 ---
        if replies:
            # 返信がある場合だけ「n件の返信を表示」という折りたたみを作る
            with st.expander(f"▼ 返信 {len(replies)} 件を表示"):
                for r in replies:
                    st.markdown(f"  **{r['name']}**: {r['content']}")
                    st.caption(f"  _{r.get('at', '')[:10]}_") # 日付を薄く表示
        
        # --- 返信を入力するボタン ---
        with st.expander("💬 返信を書く"):
            with st.form(key=f"reply_form_{p_id}", clear_on_submit=True):
                r_name = st.text_input("名前", key=f"rn_{p_id}", value="匿名希望")
                r_msg = st.text_input("返信内容", key=f"rm_{p_id}")
                if st.form_submit_button("送信"):
                    if r_name and r_msg:
                        new_reply = {"name": r_name, "content": r_msg, "at": datetime.now().isoformat()}
                        db.collection("posts").document(p_id).update({
                            "replies": firestore.ArrayUnion([new_reply])
                        })
                        st.rerun()