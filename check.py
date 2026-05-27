import streamlit as st
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

ROOMS_COLLECTION = "labstatus_rooms"

STATUS = {
    "present": {"label": "在室", "emoji": "🟢"},
    "out": {"label": "外出", "emoji": "🟠"},
    "home": {"label": "帰宅", "emoji": "⚪"},
}

INITIAL_ROOMS = [
    {"id": "main_lab", "name": "堺研究室", "room_no": "A629", "order": 1, "capacity": 10},
    {"id": "student_room", "name": "大塚研究室", "room_no": "A626", "order": 2, "capacity": 10},
    {"id": "discussion_room", "name": "土肥開発室", "room_no": "A423", "order": 3, "capacity": 10},
]


def now_text():
    return datetime.now().strftime("%H:%M")


def init_rooms():
    exists = list(db.collection(ROOMS_COLLECTION).limit(1).stream())

    if exists:
        return

    for room in INITIAL_ROOMS:
        db.collection(ROOMS_COLLECTION).document(room["id"]).set(room)


def load_rooms():
    init_rooms()
    rooms = []

    room_docs = db.collection(ROOMS_COLLECTION).order_by("order").stream()

    for room_doc in room_docs:
        room = room_doc.to_dict()
        room["id"] = room_doc.id
        room["members"] = []

        members = (
            db.collection(ROOMS_COLLECTION)
            .document(room_doc.id)
            .collection("members")
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .stream()
        )

        for member_doc in members:
            member = member_doc.to_dict()
            member["id"] = member_doc.id
            room["members"].append(member)

        rooms.append(room)

    return rooms


def add_member(room_id, name, role, status, memo):
    db.collection(ROOMS_COLLECTION).document(room_id).collection("members").add({
        "name": name,
        "role": role,
        "status": status,
        "memo": memo,
        "updated_at": now_text(),
    })


def update_member(room_id, member_id, **data):
    data["updated_at"] = now_text()
    db.collection(ROOMS_COLLECTION).document(room_id).collection("members").document(member_id).update(data)


def delete_member(room_id, member_id):
    db.collection(ROOMS_COLLECTION).document(room_id).collection("members").document(member_id).delete()


def reset_all_home(rooms):
    for room in rooms:
        for member in room["members"]:
            update_member(room["id"], member["id"], status="home")


def show_check_page():
    st.markdown(
        """
        <style>
        .main-title {
            font-size: 34px;
            font-weight: 800;
            margin-bottom: 0px;
        }
        .sub-title {
            color: #64748b;
            font-size: 15px;
            margin-bottom: 24px;
        }
        .top-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
            margin-bottom: 20px;
        }
        .room-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
            min-height: 520px;
        }
        .member-card {
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 14px;
            margin-bottom: 14px;
            background: #fbfdff;
        }
        .member-name {
            font-weight: 800;
            font-size: 18px;
        }
        .small-text {
            color: #64748b;
            font-size: 13px;
        }
        .memo-box {
            background: #f1f5f9;
            padding: 8px 10px;
            border-radius: 10px;
            margin-top: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    rooms = load_rooms()

    st.markdown('<div class="main-title">👥 研究室在室管理ボード</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Lab Occupancy & Status Board ・ 研究室メンバーの在室状況を管理</div>', unsafe_allow_html=True)

    all_members = [member for room in rooms for member in room["members"]]
    present_count = sum(1 for m in all_members if m.get("status") == "present")
    out_count = sum(1 for m in all_members if m.get("status") == "out")
    home_count = sum(1 for m in all_members if m.get("status") == "home")

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    c1.info(f"👥 登録メンバー {len(all_members)}人")
    c2.success(f"在室 {present_count}人")
    c3.warning(f"外出 {out_count}人")
    c4.info(f"帰宅 {home_count}人")

    st.markdown("---")

    with st.container(border=True):
        search = st.text_input(
            "🔍 検索",
            placeholder="メンバー名・役職・メモで検索できます",
        )

        f1, f2 = st.columns([3, 1])
        status_filter = f1.radio(
            "ステータスで絞り込み",
            ["全員", "在室", "外出", "帰宅"],
            horizontal=True,
        )

        if f2.button("全員を帰宅にする"):
            reset_all_home(rooms)
            st.rerun()

    st.markdown("")

    room_columns = st.columns(3)

    for index, room in enumerate(rooms):
        with room_columns[index % 3]:
            with st.container(border=True):
                room_name = room.get("name", "")
                room_no = room.get("room_no", "")
                capacity = room.get("capacity", 10)
                members = room["members"]

                room_present = sum(1 for m in members if m.get("status") == "present")
                room_out = sum(1 for m in members if m.get("status") == "out")

                st.subheader(f"🔵 {room_name}")
                if room_no:
                    st.caption(f"{room_no}")

                st.caption(f"登録スロット {len(members)} / {capacity}名　　在室:{room_present} 外出:{room_out}")
                st.progress(min(len(members) / capacity, 1.0))

                st.markdown("---")

                visible_members = []

                for member in members:
                    text = f"{member.get('name', '')} {member.get('role', '')} {member.get('memo', '')}"

                    if search and search.lower() not in text.lower():
                        continue

                    if status_filter != "全員":
                        status_map = {
                            "在室": "present",
                            "外出": "out",
                            "帰宅": "home",
                        }
                        if member.get("status") != status_map[status_filter]:
                            continue

                    visible_members.append(member)

                if not visible_members:
                    st.info("表示するメンバーがいません。")

                for member in visible_members:
                    member_id = member["id"]
                    status = member.get("status", "home")
                    status_info = STATUS.get(status, STATUS["home"])

                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div class="member-name">
                                {status_info["emoji"]} {member.get("name", "")}
                                <span class="small-text"> {member.get("role", "")}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.caption(f"更新：{member.get('updated_at', '')}")

                        s1, s2, s3 = st.columns(3)

                        if s1.button("在室", key=f"present_{room['id']}_{member_id}", use_container_width=True):
                            update_member(room["id"], member_id, status="present")
                            st.rerun()

                        if s2.button("外出", key=f"out_{room['id']}_{member_id}", use_container_width=True):
                            update_member(room["id"], member_id, status="out")
                            st.rerun()

                        if s3.button("帰宅", key=f"home_{room['id']}_{member_id}", use_container_width=True):
                            update_member(room["id"], member_id, status="home")
                            st.rerun()

                        memo = st.text_input(
                            "メモ",
                            value=member.get("memo", ""),
                            key=f"memo_{room['id']}_{member_id}",
                            placeholder="例：講義中、会議中、実験中",
                        )

                        m1, m2 = st.columns([3, 1])

                        if m1.button("メモ更新", key=f"memo_update_{room['id']}_{member_id}", use_container_width=True):
                            update_member(room["id"], member_id, memo=memo)
                            st.rerun()

                        if m2.button("削除", key=f"delete_{room['id']}_{member_id}", use_container_width=True):
                            delete_member(room["id"], member_id)
                            st.rerun()

                with st.expander("➕ メンバーを追加"):
                    with st.form(f"add_member_{room['id']}", clear_on_submit=True):
                        name = st.text_input("名前")
                        role = st.text_input("役職・学年", placeholder="例：M2, B4, 教員")
                        status_label = st.selectbox("初期状態", ["在室", "外出", "帰宅"])
                        memo = st.text_input("メモ", placeholder="例：論文執筆中")

                        submitted = st.form_submit_button("追加")

                        if submitted:
                            if not name:
                                st.warning("名前を入力してください。")
                            else:
                                status_map = {
                                    "在室": "present",
                                    "外出": "out",
                                    "帰宅": "home",
                                }

                                add_member(
                                    room["id"],
                                    name,
                                    role,
                                    status_map[status_label],
                                    memo,
                                )
                                st.rerun()

    st.markdown("---")
    st.markdown("[← 掲示板に戻る](./)")