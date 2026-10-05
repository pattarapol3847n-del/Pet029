from __future__ import annotations

import streamlit as st

from neo4j_service import (
    get_dashboard_metrics,
    get_profile,
    get_people,
    graph_neighborhood,
    recommend_pet,
    seed_demo_data,
    ping,
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Pet Recommendation System",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CUSTOM STYLE
# =========================================================

st.markdown(
    """
    <style>

      .block-container {
        padding-top: 1.3rem;
        padding-bottom: 2rem;
      }

      .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 22px;
        background: linear-gradient(
            120deg,
            #111827 0%,
            #1f2937 55%,
            #0f766e 100%
        );
        color: white;
        margin-bottom: 1rem;
      }

      .hero h1 {
        margin: 0;
        font-size: 2.15rem;
      }

      .hero p {
        opacity: .88;
        margin: .35rem 0 0 0;
      }

      .pet-card {
        padding: 1rem 1.1rem;
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 16px;
        margin-bottom: .75rem;
      }

      .score-pill {
        display: inline-block;
        padding: .2rem .55rem;
        border-radius: 999px;
        background: #0f766e;
        color: white;
        font-size: .8rem;
        font-weight: 700;
      }

      .muted {
        opacity: .72;
        font-size: .9rem;
      }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# CONNECTION
# =========================================================

def require_connection() -> None:

    try:

        if not ping():
            raise RuntimeError(
                "Neo4j did not return a healthy response"
            )

    except Exception as exc:

        st.error("ยังเชื่อมต่อ Neo4j Aura ไม่สำเร็จ")

        st.code(
            '[neo4j]\n'
            'uri = "neo4j+s://YOUR_INSTANCE.databases.neo4j.io"\n'
            'username = "neo4j"\n'
            'password = "YOUR_PASSWORD"\n'
            'database = "neo4j"',
            language="toml",
        )

        st.caption(
            "ให้นำค่าด้านบนไปใส่ใน Streamlit Secrets "
            "และห้าม commit password ลง GitHub"
        )

        st.exception(exc)

        st.stop()


# =========================================================
# PERSON SELECTOR
# =========================================================

def person_selector(key: str = "person") -> str:

    people = get_people()

    if not people:

        st.info(
            "ยังไม่มีข้อมูลผู้ใช้ กรุณาไปหน้า Admin / Setup "
            "แล้วสร้างข้อมูลตัวอย่าง"
        )

        st.stop()

    labels = {
        f"{x['person_id']} — {x['name']}":
        x["person_id"]
        for x in people
    }

    chosen = st.selectbox(
        "เลือกผู้ใช้",
        list(labels),
        key=key
    )

    return labels[chosen]


# =========================================================
# RECOMMENDATION REASON
# =========================================================

def explain_reason(row: dict) -> str:

    if row.get("score", 0):

        score = row["score"]

        if score >= 3:
            return (
                f"มีเพื่อน {score} คนที่เลี้ยงสัตว์ชนิดนี้ "
                "จึงเป็นสัตว์ที่ได้รับการแนะนำสูงสุด"
            )

        return (
            f"มีเพื่อน {score} คนที่เลี้ยงสัตว์ชนิดนี้"
        )

    return "แนะนำจากข้อมูลความสัมพันธ์ในเครือข่าย"


# =========================================================
# CHECK NEO4J
# =========================================================

require_connection()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.image(
        "Boat99.jpg",
        width=100
    )

    st.markdown("## 🐾 Pet Recommendation")

    st.caption("Neo4j Aura + Streamlit")

    page = st.radio(
        "เมนู",
        [
            "Dashboard",
            "Recommendations",
            "Pet Search",
            "My Pets",
            "Graph Explorer",
            "Admin / Setup",
        ],
    )

    st.divider()

    st.caption(
        "Bachelor-level Graph Database Project"
    )


# =========================================================
# HERO
# =========================================================

st.markdown(
    """
    <div class="hero">

      <h1>
        🐾 Pet Recommendation System
      </h1>

      <p>
        ระบบแนะนำสัตว์เลี้ยงด้วย Graph Database
        จากความสัมพันธ์ระหว่างผู้ใช้ เพื่อน และสัตว์เลี้ยง
      </p>

    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DASHBOARD
# =========================================================

if page == "Dashboard":

    st.subheader("ภาพรวมระบบ")

    m = get_dashboard_metrics()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "People",
        m.get("people", 0)
    )

    c2.metric(
        "Pets",
        m.get("pets", 0)
    )

    c3.metric(
        "Has Pet relationships",
        m.get("has_pets", 0)
    )

    c4.metric(
        "Friend relationships",
        m.get("friendships", 0)
    )

    st.divider()

    person_id = person_selector(
        "dash_person"
    )

    profile = get_profile(person_id)

    if profile:

        left, right = st.columns([1, 2])

        with left:

            st.markdown(
                f"### {profile['name']}"
            )

            st.write(
                f"**รหัส:** {profile['person_id']}"
            )

            st.write(
                "**สัตว์เลี้ยงที่มี:** "
                +
                (
                    ", ".join(
                        profile.get("pets", [])
                    )
                    or "ยังไม่มี"
                )
            )

        with right:

            st.markdown(
                "### เพื่อน"
            )

            friends = profile.get(
                "friends",
                []
            )

            if friends:

                for friend in friends:

                    st.write(
                        f"👤 {friend}"
                    )

            else:

                st.info(
                    "ยังไม่มีข้อมูลเพื่อน"
                )


# =========================================================
# RECOMMENDATIONS
# =========================================================

elif page == "Recommendations":

    st.subheader(
        "✨ สัตว์เลี้ยงที่แนะนำ"
    )

    person_id = person_selector(
        "rec_person"
    )

    top_n = st.slider(
        "จำนวนคำแนะนำ",
        1,
        6,
        6
    )

    rows = recommend_pet(
        person_id
    )

    rows = rows[:top_n]

    st.caption(
        "คะแนน = จำนวนเพื่อนที่เลี้ยงสัตว์ชนิดนั้น"
    )

    if not rows:

        st.info(
            "ยังไม่มีคำแนะนำสำหรับผู้ใช้นี้"
        )

    for i, row in enumerate(
        rows,
        start=1
    ):

        pet_name = row.get(
            "pet",
            "ไม่ระบุ"
        )

        score = row.get(
            "score",
            0
        )

        st.markdown(
            f"""
            <div class="pet-card">

              <span class="score-pill">
                #{i} · score {score}
              </span>

              <h3 style="margin:.55rem 0 .2rem 0">
                🐾 {pet_name}
              </h3>

              <div class="muted">
                Pet Recommendation
              </div>

              <p>
                <b>เหตุผล:</b>
                {explain_reason(row)}
              </p>

            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# PET SEARCH
# =========================================================

elif page == "Pet Search":

    st.subheader(
        "🔎 ค้นหาสัตว์เลี้ยง"
    )

    pet_names = [
        "Dog",
        "Cat",
        "Rabbit",
        "Bird",
        "Fish",
        "Hamster",
    ]

    keyword = st.text_input(
        "ชื่อสัตว์เลี้ยง",
        placeholder="เช่น Cat, Dog, Rabbit"
    )

    if keyword:

        results = [
            pet
            for pet in pet_names
            if keyword.lower()
            in pet.lower()
        ]

    else:

        results = pet_names

    st.write(
        f"พบ {len(results)} รายการ"
    )

    for pet in results:

        st.markdown(
            f"""
            <div class="pet-card">

              <h3>
                🐾 {pet}
              </h3>

              <div class="muted">
                Pet
              </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# MY PETS
# =========================================================

elif page == "My Pets":

    st.subheader(
        "🐾 สัตว์เลี้ยงของฉัน"
    )

    person_id = person_selector(
        "my_pet_person"
    )

    profile = get_profile(
        person_id
    )

    if profile:

        pets = profile.get(
            "pets",
            []
        )

        if pets:

            for pet in pets:

                st.markdown(
                    f"""
                    <div class="pet-card">

                      <h3>
                        🐾 {pet}
                      </h3>

                      <div class="muted">
                        สัตว์เลี้ยงของผู้ใช้
                      </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        else:

            st.info(
                "ผู้ใช้นี้ยังไม่มีสัตว์เลี้ยง"
            )


# =========================================================
# GRAPH EXPLORER
# =========================================================

elif page == "Graph Explorer":

    st.subheader(
        "🕸️ Graph Explorer"
    )

    person_id = person_selector(
        "graph_person"
    )

    rows = graph_neighborhood(
        person_id
    )

    if not rows:

        st.info(
            "ยังไม่มี neighborhood graph"
        )

    else:

        dot = [
            "digraph G {",
            'rankdir="LR";',
            'node [shape=box, style="rounded,filled", fillcolor="#f8fafc"];'
        ]

        seen_nodes = set()

        for r in rows:

            for nid, label, name in [
                (
                    r["source_id"],
                    r["source_label"],
                    r["source_name"]
                ),
                (
                    r["target_id"],
                    r["target_label"],
                    r["target_name"]
                ),
            ]:

                if nid not in seen_nodes:

                    safe_name = (
                        str(name)
                        .replace('"', "'")
                    )

                    dot.append(
                        f'"{nid}" '
                        f'[label="{safe_name}\\n:{label}"];'
                    )

                    seen_nodes.add(nid)

            dot.append(
                f'"{r["source_id"]}" '
                f'-> '
                f'"{r["target_id"]}" '
                f'[label="{r["relationship"]}"];'
            )

        dot.append("}")

        st.graphviz_chart(
            "\n".join(dot),
            use_container_width=True
        )

        with st.expander(
            "ดูข้อมูลความสัมพันธ์ที่ใช้วาดกราฟ"
        ):

            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True
            )


# =========================================================
# ADMIN / SETUP
# =========================================================

elif page == "Admin / Setup":

    st.subheader(
        "⚙️ Setup ข้อมูลตัวอย่าง"
    )

    st.warning(
        "ปุ่มนี้ไม่ลบข้อมูลเดิม "
        "และใช้ MERGE จึงสามารถกดซ้ำได้"
    )

    st.markdown(
        """
        **Graph schema**

        - `(:Person)-[:FRIEND_OF]-(:Person)`
        - `(:Person)-[:HAS_PET]->(:Pet)`

        **Recommendation**

        ระบบจะแนะนำสัตว์เลี้ยงจากสัตว์ที่
        เพื่อนของผู้ใช้เลี้ยงอยู่
        และจะไม่แนะนำสัตว์ที่ผู้ใช้มีอยู่แล้ว
        """
    )

    if st.button(
        "สร้าง Constraint + Demo Data",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "กำลังสร้างข้อมูล..."
        ):

            seed_demo_data()

        st.success(
            "สร้างข้อมูลตัวอย่างเรียบร้อยแล้ว"
        )

        st.rerun()