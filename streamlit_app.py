"""
Streamlit Frontend for AI-Driven Adaptive Diagnostic Engine
Run with: streamlit run streamlit_app.py
Make sure FastAPI backend is running on http://localhost:8000
"""

import streamlit as st
import requests

API_BASE = "http://localhost:8000/api/v1"

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Adaptive Diagnostic Engine",
    page_icon="🧠",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Space Mono', monospace; }

    .main { background-color: #0f0f0f; }

    .question-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 24px;
        margin: 16px 0;
        color: white;
    }
    .score-box {
        background: linear-gradient(135deg, #0f3460 0%, #533483 100%);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        color: white;
        font-family: 'Space Mono', monospace;
    }
    .correct { color: #00ff88; font-weight: bold; }
    .incorrect { color: #ff4444; font-weight: bold; }
    .topic-tag {
        background: #0f3460;
        color: #e0e0e0;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-block;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ── Session State Init ────────────────────────────────────────────────────────
for key, val in {
    "session_id": None,
    "question": None,
    "ability_score": 0.5,
    "questions_answered": 0,
    "last_result": None,
    "test_complete": False,
    "results": None,
    "user_id": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── Helper Functions ──────────────────────────────────────────────────────────
def start_test(user_id: str):
    try:
        r = requests.post(f"{API_BASE}/start-test", json={"user_id": user_id}, timeout=10)
        r.raise_for_status()
        data = r.json()
        st.session_state.session_id = data["session_id"]
        st.session_state.question = data["question"]
        st.session_state.ability_score = data["ability_score"]
        st.session_state.questions_answered = 0
        st.session_state.last_result = None
        st.session_state.test_complete = False
        st.session_state.results = None
        return True
    except Exception as e:
        st.error(f"Could not start test: {e}")
        return False


def submit_answer(selected_answer: str):
    try:
        r = requests.post(f"{API_BASE}/submit-answer", json={
            "session_id": st.session_state.session_id,
            "question_id": st.session_state.question["id"],
            "selected_answer": selected_answer,
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        st.session_state.ability_score = data["ability_score"]
        st.session_state.questions_answered = data["questions_answered"]
        st.session_state.last_result = {
            "is_correct": data["is_correct"],
            "correct_answer": data["correct_answer"],
            "selected": selected_answer,
        }
        if data["is_complete"]:
            st.session_state.test_complete = True
            st.session_state.question = None
            fetch_results()
        else:
            st.session_state.question = data.get("next_question")
        return True
    except Exception as e:
        st.error(f"Error submitting answer: {e}")
        return False


def fetch_results():
    try:
        r = requests.get(f"{API_BASE}/results/{st.session_state.session_id}", timeout=15)
        r.raise_for_status()
        st.session_state.results = r.json()
    except Exception as e:
        st.error(f"Could not fetch results: {e}")


# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("# 🧠 Adaptive Diagnostic Engine")
st.markdown("*IRT-powered GRE-style adaptive test*")
st.divider()

# ── Start Screen ──────────────────────────────────────────────────────────────
if st.session_state.session_id is None:
    st.markdown("### Enter your name to begin")
    name = st.text_input("Your Name", placeholder="e.g. Abhishek", key="name_input")
    if st.button("🚀 Start Test", use_container_width=True, type="primary"):
        if name.strip():
            with st.spinner("Setting up your test..."):
                if start_test(name.strip()):
                    st.session_state.user_id = name.strip()
                    st.rerun()
        else:
            st.warning("Please enter your name first!")

# ── Test Complete Screen ───────────────────────────────────────────────────────
elif st.session_state.test_complete:
    res = st.session_state.results
    st.markdown("## 🎉 Test Complete!")
    st.divider()

    if res:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""<div class="score-box">
                <div style="font-size:12px;opacity:0.7">ABILITY SCORE</div>
                <div style="font-size:32px;font-weight:bold">{res['final_ability_score']:.2f}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="score-box">
                <div style="font-size:12px;opacity:0.7">ACCURACY</div>
                <div style="font-size:32px;font-weight:bold">{res['accuracy']*100:.0f}%</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="score-box">
                <div style="font-size:12px;opacity:0.7">QUESTIONS</div>
                <div style="font-size:32px;font-weight:bold">{res['questions_answered']}</div>
            </div>""", unsafe_allow_html=True)

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**❌ Topics Missed**")
            if res["topics_missed"]:
                for t in res["topics_missed"]:
                    st.markdown(f'<span class="topic-tag">🔴 {t}</span>', unsafe_allow_html=True)
            else:
                st.success("None! Perfect score!")

        with col_b:
            st.markdown("**✅ Topics Correct**")
            if res["topics_correct"]:
                for t in res["topics_correct"]:
                    st.markdown(f'<span class="topic-tag">🟢 {t}</span>', unsafe_allow_html=True)
            else:
                st.info("Keep practicing!")

        if res.get("study_plan"):
            st.divider()
            st.markdown("### 📚 Your Personalised Study Plan")
            st.info(res["study_plan"])

    if st.button("🔄 Take Another Test", use_container_width=True):
        for key in ["session_id", "question", "ability_score", "questions_answered",
                    "last_result", "test_complete", "results", "user_id"]:
            st.session_state[key] = None if key != "ability_score" else 0.5
            if key in ["questions_answered"]:
                st.session_state[key] = 0
            if key in ["test_complete"]:
                st.session_state[key] = False
        st.rerun()

# ── Active Test Screen ─────────────────────────────────────────────────────────
else:
    # Progress bar
    progress = st.session_state.questions_answered / 10
    st.progress(progress, text=f"Question {st.session_state.questions_answered + 1} of 10")

    # Ability score display
    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown(f"""<div class="score-box">
            <div style="font-size:11px;opacity:0.7">ABILITY</div>
            <div style="font-size:24px;font-weight:bold">{st.session_state.ability_score:.2f}</div>
        </div>""", unsafe_allow_html=True)

    # Last result feedback
    if st.session_state.last_result:
        lr = st.session_state.last_result
        if lr["is_correct"]:
            st.markdown(f'<p class="correct">✅ Correct! Well done.</p>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<p class="incorrect">❌ Incorrect. Correct answer was: <b>{lr["correct_answer"]}</b></p>',
                unsafe_allow_html=True
            )

    # Question display
    if st.session_state.question:
        q = st.session_state.question
        st.markdown(f"""<div class="question-box">
            <span class="topic-tag">{q['topic']}</span>
            <span class="topic-tag">Difficulty: {q['difficulty']:.1f}</span>
            <br><br>
            <b style="font-size:18px">{q['question_text']}</b>
        </div>""", unsafe_allow_html=True)

        selected = st.radio(
            "Choose your answer:",
            options=q["options"],
            key=f"answer_{q['id']}",
            index=None,
        )

        if st.button("✅ Submit Answer", use_container_width=True, type="primary", disabled=selected is None):
            with st.spinner("Checking..."):
                submit_answer(selected)
                st.rerun()
    else:
        st.warning("Loading next question...")
        if st.button("Refresh"):
            st.rerun()