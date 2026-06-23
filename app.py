import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from openai import OpenAI
import json

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IAS AI Tutor",
    page_icon="🎓",
    layout="centered"
)

# ── Styling ────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; box-sizing: border-box; }

    .stApp {
        background: #000000;
        min-height: 100vh;
    }

    header[data-testid="stHeader"] { background: transparent; }

    /* ── Home screen ── */
    .home-title {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 600;
        text-align: center;
        margin: 40px 0 36px 0;
        letter-spacing: 0.5px;
    }

    .subject-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        max-width: 520px;
        margin: 0 auto 16px auto;
    }

    .subject-card {
        background: #000;
        border-radius: 6px;
        padding: 40px 20px;
        text-align: center;
        cursor: pointer;
        font-size: 1.3rem;
        font-weight: 500;
        color: #ffffff;
        transition: background 0.2s ease;
        position: relative;
    }

    /* Individual border colours matching the mockup */
    .subject-card.manfin  { border: 2px solid; border-image: linear-gradient(135deg, #00eaff, #7b2fff) 1; }
    .subject-card.audit   { border: 2px solid; border-image: linear-gradient(135deg, #7b2fff, #00eaff) 1; }
    .subject-card.tax     { border: 2px solid; border-image: linear-gradient(135deg, #ff00c8, #7b2fff) 1; }
    .subject-card.finacc  { border: 2px solid; border-image: linear-gradient(135deg, #00ff85, #7b2fff) 1; }

    .subject-card-full {
        background: #000;
        border-radius: 6px;
        padding: 24px 20px;
        text-align: center;
        cursor: pointer;
        font-size: 1.3rem;
        font-weight: 500;
        color: #ffffff;
        max-width: 520px;
        margin: 0 auto;
        border: 2px solid;
        border-image: linear-gradient(90deg, #0040ff, #00eaff) 1;
    }

    /* ── Task list screen ── */
    .screen-title {
        color: #ffffff;
        font-size: 1.2rem;
        font-weight: 600;
        text-align: center;
        border: 1px solid #ffffff;
        border-radius: 4px;
        padding: 14px 20px;
        margin: 32px auto 24px auto;
        max-width: 520px;
    }

    .task-card {
        background: #000;
        border-radius: 4px;
        padding: 18px 20px;
        margin: 0 auto 12px auto;
        max-width: 520px;
        cursor: pointer;
        border: 1.5px solid transparent;
        background-clip: padding-box;
        position: relative;
        color: #ffffff;
    }

    .task-card::before {
        content: "";
        position: absolute;
        inset: -1.5px;
        border-radius: 4px;
        padding: 1.5px;
        background: linear-gradient(90deg, #00eaff, #7b2fff);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: destination-out;
        mask-composite: exclude;
        pointer-events: none;
    }

    .task-card-title {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .task-card-desc {
        font-size: 0.85rem;
        color: #aaaaaa;
    }

    .more-tasks-note {
        background: #000;
        border-radius: 4px;
        padding: 18px 20px;
        margin: 0 auto 12px auto;
        max-width: 520px;
        text-align: center;
        color: #aaaaaa;
        font-size: 0.9rem;
        border: 1.5px solid transparent;
        position: relative;
    }

    .more-tasks-note::before {
        content: "";
        position: absolute;
        inset: -1.5px;
        border-radius: 4px;
        padding: 1.5px;
        background: linear-gradient(90deg, #00eaff, #7b2fff);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: destination-out;
        mask-composite: exclude;
        pointer-events: none;
    }

    /* ── Answer screen ── */
    .answer-header {
        color: #ffffff;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 28px 0 6px 0;
    }

    .answer-body {
        color: #cccccc;
        font-size: 0.92rem;
        line-height: 1.7;
        margin-bottom: 20px;
    }

    .field-label {
        color: #ffffff;
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 6px;
    }

    /* Input styling — dark background to match mockup */
    .stTextInput > div > div > input {
        background: #000000 !important;
        color: #ffffff !important;
        border: 1.5px solid transparent !important;
        border-radius: 4px !important;
        font-size: 0.95rem !important;
        padding: 10px 14px !important;
        outline: none !important;
        background-image: linear-gradient(#000, #000),
                          linear-gradient(90deg, #00eaff, #7b2fff) !important;
        background-origin: border-box !important;
        background-clip: padding-box, border-box !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    .stTextInput label,
    .stTextArea label { display: none !important; }

    .stTextArea > div > div > textarea {
        background: #000000 !important;
        color: #ffffff !important;
        border: 1.5px solid transparent !important;
        border-radius: 4px !important;
        font-size: 0.92rem !important;
        line-height: 1.7 !important;
        padding: 12px 14px !important;
        outline: none !important;
        background-image: linear-gradient(#000, #000),
                          linear-gradient(90deg, #00eaff, #7b2fff) !important;
        background-origin: border-box !important;
        background-clip: padding-box, border-box !important;
    }

    .stTextArea > div > div > textarea:focus {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    /* Submit button */
    .stButton > button {
        background: #5cb800 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 12px 40px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
        display: block !important;
        margin: 0 auto !important;
        transition: background 0.2s ease !important;
        box-shadow: none !important;
    }

    .stButton > button:hover {
        background: #4aa000 !important;
        transform: none !important;
    }

    /* Back link */
    .back-link {
        color: #888888;
        font-size: 0.82rem;
        cursor: pointer;
        margin-bottom: 8px;
        display: inline-block;
    }

    /* ── Result cards ── */
    .score-display {
        border: 1.5px solid transparent;
        border-radius: 6px;
        padding: 24px;
        text-align: center;
        margin-bottom: 20px;
        background-image: linear-gradient(#000, #000),
                          linear-gradient(90deg, #00eaff, #7b2fff);
        background-origin: border-box;
        background-clip: padding-box, border-box;
    }

    .score-number {
        font-size: 4rem;
        font-weight: 700;
        color: #5cb800;
        line-height: 1;
    }

    .score-label {
        color: #888;
        font-size: 0.82rem;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .grade-badge {
        display: inline-block;
        padding: 6px 18px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.88rem;
        margin-top: 12px;
    }

    .grade-pass       { background: rgba(92,184,0,0.12);  color: #5cb800; border: 1px solid rgba(92,184,0,0.35); }
    .grade-borderline { background: rgba(255,165,0,0.12); color: #FFA500; border: 1px solid rgba(255,165,0,0.35); }
    .grade-fail       { background: rgba(255,80,80,0.12); color: #FF5050; border: 1px solid rgba(255,80,80,0.35); }

    .result-card {
        border-radius: 6px;
        padding: 18px 20px;
        margin-bottom: 12px;
        background: #0d0d0d;
    }

    .result-card h4 {
        margin: 0 0 8px 0;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 700;
    }

    .result-card p {
        margin: 0;
        color: #cccccc;
        line-height: 1.7;
        font-size: 0.9rem;
    }

    .card-strengths  { border-left: 3px solid #5cb800; }
    .card-strengths h4 { color: #5cb800; }
    .card-weaknesses { border-left: 3px solid #FFA500; }
    .card-weaknesses h4 { color: #FFA500; }
    .card-feedback   { border-left: 3px solid #4A9EFF; }
    .card-feedback h4 { color: #4A9EFF; }

    /* Footer */
    .ias-footer {
        text-align: center;
        color: #333;
        font-size: 0.72rem;
        margin-top: 48px;
        padding-top: 16px;
        border-top: 1px solid #1a1a1a;
        letter-spacing: 1px;
    }

    /* Spinner */
    .stSpinner > div { border-top-color: #5cb800 !important; }

    /* Warning */
    div[data-testid="stAlert"] {
        background: rgba(255,165,0,0.06) !important;
        border: 1px solid rgba(255,165,0,0.25) !important;
        border-radius: 6px !important;
        color: #FFA500 !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Clients ────────────────────────────────────────────────────────────────────

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def get_google_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    return gspread.authorize(creds)


# ── Data helpers ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_scenarios():
    gc = get_google_client()
    rows = gc.open("AI Tutor Scenarios").sheet1.get_all_records()
    return rows


def get_tasks_for_subject(subject):
    rows = load_scenarios()
    return [r for r in rows if str(r.get("Subject", "")).strip().lower() == subject.lower()]


def grade_answer(scenario_text, question_text, student_answer):
    prompt = f"""You are an academic tutor at the Institute of Accounting Science.

Scenario:
{scenario_text}

Question:
{question_text}

Student Answer:
{student_answer}

Grade the student's answer out of 100 based on understanding, analysis, evidence and recommendations.

Return ONLY valid JSON with no extra text:
{{
    "score": 0,
    "strengths": [],
    "weaknesses": [],
    "feedback": ""
}}"""
    response = client.responses.create(model="gpt-5", input=prompt)
    return json.loads(response.output_text)


def log_submission(student_id, subject, scenario_id, attempt, score,
                   response_text, strengths, weaknesses, feedback):
    gc = get_google_client()
    sheet = gc.open("AI Tutor Results").sheet1
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        student_id,
        subject,
        scenario_id,
        attempt,
        score,
        response_text,
        strengths,
        weaknesses,
        feedback
    ])


# ── Session state defaults ─────────────────────────────────────────────────────

for key, default in {
    "screen": "home",       # home | tasks | answer | result
    "subject": None,
    "task": None,
    "result": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Navigation helpers ─────────────────────────────────────────────────────────

def go_home():
    st.session_state.screen = "home"
    st.session_state.subject = None
    st.session_state.task = None
    st.session_state.result = None


def go_tasks(subject):
    st.session_state.subject = subject
    st.session_state.screen = "tasks"
    st.session_state.task = None
    st.session_state.result = None


def go_answer(task):
    st.session_state.task = task
    st.session_state.screen = "answer"
    st.session_state.result = None


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — Home
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.screen == "home":

    st.markdown('<div class="home-title">IAS AI Tutor</div>', unsafe_allow_html=True)

    # 2×2 grid: Manfin | Audit  /  Tax | Finacc
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Manfin", key="btn_manfin", use_container_width=True):
            go_tasks("Manfin")
            st.rerun()
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        if st.button("Tax", key="btn_tax", use_container_width=True):
            go_tasks("Tax")
            st.rerun()

    with col2:
        if st.button("Audit", key="btn_audit", use_container_width=True):
            go_tasks("Audit")
            st.rerun()
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        if st.button("Finacc", key="btn_finacc", use_container_width=True):
            go_tasks("Finacc")
            st.rerun()

    # Full-width Integrated below
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    if st.button("Integrated", key="btn_integrated", use_container_width=True):
        go_tasks("Integrated")
        st.rerun()

    st.markdown('<div class="ias-footer">INSTITUTE OF ACCOUNTING SCIENCE · AI TUTOR · CONFIDENTIAL</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — Task list
# ══════════════════════════════════════════════════════════════════════════════

elif st.session_state.screen == "tasks":

    subject = st.session_state.subject

    if st.button("← Back", key="back_home"):
        go_home()
        st.rerun()

    st.markdown(f'<div class="screen-title">{subject} — Select your task</div>',
                unsafe_allow_html=True)

    with st.spinner("Loading tasks..."):
        tasks = get_tasks_for_subject(subject)

    if not tasks:
        st.warning(f"No tasks found for {subject} yet. Check back soon.")
    else:
        for i, task in enumerate(tasks):
            title = task.get("Title", f"Task {i+1}")
            scenario_preview = str(task.get("Scenario", ""))[:100] + "…"
            if st.button(f"**{title}**\n\n{scenario_preview}", key=f"task_{i}",
                         use_container_width=True):
                go_answer(task)
                st.rerun()

    st.markdown(
        '<div class="more-tasks-note">More tasks will be available as time continues</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="ias-footer">INSTITUTE OF ACCOUNTING SCIENCE · AI TUTOR · CONFIDENTIAL</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — Answer
# ══════════════════════════════════════════════════════════════════════════════

elif st.session_state.screen == "answer":

    task = st.session_state.task

    if st.button("← Back to tasks", key="back_tasks"):
        st.session_state.screen = "tasks"
        st.session_state.result = None
        st.rerun()

    title    = task.get("Title", "Task")
    scenario = task.get("Scenario", "")
    question = task.get("Question", "")

    st.markdown(f'<div class="answer-header">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="answer-body"><strong>Scenario</strong><br>{scenario}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="answer-body"><strong>Question</strong><br>{question}</div>',
                unsafe_allow_html=True)

    st.markdown('<div class="field-label">Student Number</div>', unsafe_allow_html=True)
    student_id = st.text_input("Student Number", placeholder="e.g. 20222526",
                               label_visibility="collapsed")

    st.markdown('<div class="field-label" style="margin-top:14px;">Your answer</div>',
                unsafe_allow_html=True)
    answer = st.text_area("Your answer",
                          placeholder="Write your answer here...",
                          height=200,
                          label_visibility="collapsed")

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    if st.button("SUBMIT"):
        if not student_id.strip():
            st.warning("⚠️ Student Number is required before submitting.")
        elif not answer.strip():
            st.warning("⚠️ Please write your answer before submitting.")
        else:
            with st.spinner("Analysing your answer..."):
                result = grade_answer(scenario, question, answer)

            st.session_state.result = {
                "score":     result["score"],
                "strengths": ", ".join(result["strengths"]),
                "weaknesses": ", ".join(result["weaknesses"]),
                "feedback":  result["feedback"],
                "student_id": student_id,
                "answer":    answer,
            }

            try:
                log_submission(
                    student_id  = student_id,
                    subject     = st.session_state.subject,
                    scenario_id = task.get("ScenarioID", ""),
                    attempt     = 1,
                    score       = result["score"],
                    response_text = answer,
                    strengths   = ", ".join(result["strengths"]),
                    weaknesses  = ", ".join(result["weaknesses"]),
                    feedback    = result["feedback"],
                )
            except Exception:
                pass  # Don't block result display if logging fails

            st.session_state.screen = "result"
            st.rerun()

    st.markdown('<div class="ias-footer">INSTITUTE OF ACCOUNTING SCIENCE · AI TUTOR · CONFIDENTIAL</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — Result
# ══════════════════════════════════════════════════════════════════════════════

elif st.session_state.screen == "result":

    r = st.session_state.result
    score = r["score"]

    if score >= 75:
        grade_class, grade_label = "grade-pass",       "✅ Pass"
    elif score >= 50:
        grade_class, grade_label = "grade-borderline", "⚠️ Borderline"
    else:
        grade_class, grade_label = "grade-fail",       "❌ Needs Work"

    st.markdown(f"""
        <div class="score-display">
            <div class="score-number">{score}</div>
            <div class="score-label">out of 100</div>
            <div class="grade-badge {grade_class}">{grade_label}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="result-card card-strengths">
            <h4>💪 Strengths</h4>
            <p>{r["strengths"]}</p>
        </div>
        <div class="result-card card-weaknesses">
            <h4>⚠️ Areas to Improve</h4>
            <p>{r["weaknesses"]}</p>
        </div>
        <div class="result-card card-feedback">
            <h4>💡 Tutor Feedback</h4>
            <p>{r["feedback"]}</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Try another task", use_container_width=True):
            st.session_state.screen = "tasks"
            st.session_state.result = None
            st.rerun()
    with col2:
        if st.button("Back to subjects", use_container_width=True):
            go_home()
            st.rerun()

    st.markdown('<div class="ias-footer">INSTITUTE OF ACCOUNTING SCIENCE · AI TUTOR · CONFIDENTIAL</div>',
                unsafe_allow_html=True)
    
    #This will be the base app going forward 