import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime, timezone

# ==========================================
# Firebase 初期化
# ==========================================

if not firebase_admin._apps:
    raw_json = st.secrets["firebase"]["json_data"]

    firebase_info = json.loads(raw_json)

    firebase_info["private_key"] = firebase_info["private_key"].replace("\\n", "\n")

    cred = credentials.Certificate(firebase_info)

    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================================
# ページ設定
# ==========================================

st.set_page_config(
    page_title="研究室在室管理",
    layout="wide"
)

st.title("👀 研究室在室管理")

st.caption("研究室メンバーの在室状況を管理します。")

# ==========================================
# Firestore コレクション
# ==========================================

ROOMS_COLLECTION = "labstatus_rooms"

# ==========================================
# 状態表示
# ==========================================

STATUS_LABELS = {
    "present": "🟢 在室",
    "out": "🟠 外出",
    "home": "⚪ 帰宅",
}

# ==========================================
# 初期部屋データ
# ==========================================

INITIAL_ROOMS = [
    {
        "id": "room1",
        "name": "メイン研究室",
        "order": 1
    },
    {
        "id": "room2",
        "name": "学生室",
        "order": 2
    },
    {
        "id": "room3",
        "name": "作業室",
        "order": 3
    }
]

# ==========================================
# 現在時刻
# ==========================================

def now():
    return datetime.now(timezone.utc).isoformat()

# ==========================================
# 初期部屋作成
# ==========================================

def init_rooms():

    exists = list(
        db.collection(ROOMS_COLLECTION)
        .limit(1)
        .stream()
    )

    if exists:
        return

    for room in INITIAL_ROOMS:

        db.collection(ROOMS_COLLECTION)\
            .document(room["id"])\
            .set(room)

# ==========================================
# 部屋読み込み
# ==========================================

def load_rooms():

    init_rooms()

    rooms = []

    room_docs = (
        db.collection(ROOMS_COLLECTION)
        .order_by("order")
        .stream()
    )

    for room_doc in room_docs:

        room = room_doc.to_dict()

        room["id"] = room_doc.id

        room["members"] = []

        member_docs = (
            db.collection(ROOMS_COLLECTION)
            .document(room_doc.id)
            .collection("members")
            .order_by(
                "updated_at",
                direction=firestore.Query.DESCENDING
            )
            .stream()
        )

        for member_doc in member_docs:

            member = member_doc.to_dict()

            member["id"] = member_doc.id

            room["members"].append(member)

        rooms.append(room)

    return rooms

# ==========================================
# メンバー追加
# ==========================================

def add_member(room_id, name, status, memo):

    db.collection(ROOMS_COLLECTION)\
        .document(room_id)\
        .collection("members")\
        .add({
            "name": name,
            "status": status,
            "memo": memo,
            "updated_at": now(),
        })

# ==========================================
# メンバー更新
# ==========================================

def update_member(room_id, member_id, **data):

    data["updated_at"] = now()

    db.collection(ROOMS_COLLECTION)\
        .document(room_id)\
        .collection("members")\
        .document(member_id)\
        .update(data)

# ==========================================
# メンバー削除
# ==========================================

def delete_member(room_id, member_id):

    db.collection(ROOMS_COLLECTION)\
        .document(room_id)\
        .collection("members")\
        .document(member_id)\
        .delete()

# ==========================================
# データ読み込み
# ==========================================

rooms = load_rooms()

# ==========================================
# 統計表示
# ==========================================

present_count = sum(
    1
    for room in rooms
    for member in room["members"]
    if member.get("status") == "present"
)

out_count = sum(
    1
    for room in rooms
    for member in room["members"]
    if member.get("status") == "out"
)

home_count = sum(
    1
    for room in rooms
    for member in room["members"]
    if member.get("status") == "home"
)

c1, c2, c3 = st.columns(3)

c1.metric("在室", f"{present_count}人")

c2.metric("外出", f"{out_count}人")

c3.metric("帰宅", f"{home_count}人")

st.divider()

# ==========================================
# 部屋表示
# ==========================================

for room in rooms:

    with st.container(border=True):

        st.subheader(f"🏢 {room['name']}")

        if not room["members"]:

            st.info("まだメンバーが登録されていません。")

        for member in room["members"]:

            member_id = member["id"]

            current_status = member.get("status", "home")

            with st.container(border=True):

                st.markdown(f"### {member.get('name', '')}")

                st.write(
                    f"状態：{STATUS_LABELS.get(current_status, '⚪ 帰宅')}"
                )

                st.caption(
                    f"メモ：{member.get('memo', '') or 'なし'}"
                )

                cols = st.columns(4)

                if cols[0].button(
                    "在室",
                    key=f"present_{room['id']}_{member_id}"
                ):

                    update_member(
                        room["id"],
                        member_id,
                        status="present"
                    )

                    st.rerun()

                if cols[1].button(
                    "外出",
                    key=f"out_{room['id']}_{member_id}"
                ):

                    update_member(
                        room["id"],
                        member_id,
                        status="out"
                    )

                    st.rerun()

                if cols[2].button(
                    "帰宅",
                    key=f"home_{room['id']}_{member_id}"
                ):

                    update_member(
                        room["id"],
                        member_id,
                        status="home"
                    )

                    st.rerun()

                if cols[3].button(
                    "削除",
                    key=f"delete_{room['id']}_{member_id}"
                ):

                    delete_member(
                        room["id"],
                        member_id
                    )

                    st.rerun()

                new_memo = st.text_input(
                    "メモ更新",
                    value=member.get("memo", ""),
                    key=f"memo_{room['id']}_{member_id}"
                )

                if new_memo != member.get("memo", ""):

                    update_member(
                        room["id"],
                        member_id,
                        memo=new_memo
                    )

                    st.rerun()

        with st.expander("➕ メンバー追加"):

            with st.form(
                f"add_member_{room['id']}",
                clear_on_submit=True
            ):

                name = st.text_input("名前")

                status_label = st.selectbox(
                    "初期状態",
                    ["在室", "外出", "帰宅"]
                )

                memo = st.text_input("メモ")

                submitted = st.form_submit_button("追加")

                if submitted:

                    if name:

                        label_to_status = {
                            "在室": "present",
                            "外出": "out",
                            "帰宅": "home",
                        }

                        add_member(
                            room["id"],
                            name,
                            label_to_status[status_label],
                            memo
                        )

                        st.rerun()

                    else:

                        st.warning("名前を入力してください。")