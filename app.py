import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from openai import OpenAI
import json
import random

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IAS AI Tutor",
    page_icon="🎓",
    layout="centered"
)

# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');

        * {
            font-family: 'Inter', sans-serif;
        }

        /* Dark background */
        .stApp {
            background-color: #1C1C1C;
        }

        /* Hide streamlit default header */
        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* Animated header */
        .ias-header {
            background: linear-gradient(135deg, #6ABF1E 0%, #3d7a0a 100%);
            padding: 30px 20px;
            border-radius: 16px;
            text-align: center;
            margin-bottom: 24px;
            box-shadow: 0 8px 32px rgba(106, 191, 30, 0.3);
            animation: fadeInDown 0.6s ease;
        }

        .ias-header h1 {
            color: white;
            font-size: 2.2rem;
            font-weight: 900;
            margin: 0;
            letter-spacing: -0.5px;
        }

        .ias-header p {
            color: rgba(255,255,255,0.85);
            margin: 8px 0 0 0;
            font-size: 1rem;
        }

        /* Scenario card */
        .scenario-box {
            background: #2A2A2A;
            border: 1px solid #3A3A3A;
            border-left: 5px solid #6ABF1E;
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            animation: fadeInUp 0.5s ease;
        }

        .scenario-box h3 {
            color: #6ABF1E;
            margin-top: 0;
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .scenario-box p {
            color: #E0E0E0;
            line-height: 1.7;
            font-size: 0.95rem;
        }

        /* Section labels */
        .section-label {
            color: #6ABF1E;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 6px;
        }

        /* White text inputs */
        .stTextInput > div > div > input {
            background-color: #FFFFFF !important;
            color: #1A1A1A !important;
            border: 2px solid #3A3A3A !important;
            border-radius: 10px !important;
            font-size: 1rem !important;
            padding: 10px 14px !important;
        }

        .stTextInput > div > div > input:focus {
            border-color: #6ABF1E !important;
            box-shadow: 0 0 0 3px rgba(106,191,30,0.2) !important;
        }

        /* White text area */
        .stTextArea > div > div > textarea {
            background-color: #FFFFFF !important;
            color: #1A1A1A !important;
            border: 2px solid #3A3A3A !important;
            border-radius: 10px !important;
            font-size: 0.95rem !important;
            line-height: 1.6 !important;
        }

        .stTextArea > div > div > textarea:focus {
            border-color: #6ABF1E !important;
            box-shadow: 0 0 0 3px rgba(106,191,30,0.2) !important;
        }

        /* Input labels */
        .stTextInput label, .stTextArea label {
            color: #AAAAAA !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
        }

        /* Primary submit button */
        div[data-testid="stButton"] > button[kind="primary"],
        .stButton > button {
            background: linear-gradient(135deg, #6ABF1E, #58A015) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 12px 24px !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            width: 100% !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 4px 15px rgba(106,191,30,0.3) !important;
        }

        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(106,191,30,0.4) !important;
        }

        /* Result cards */
        .result-card {
            background: #2A2A2A;
            border: 1px solid #3A3A3A;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            animation: fadeInUp 0.4s ease;
        }

        .result-card h4 {
            margin: 0 0 10px 0;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: 700;
        }

        .result-card p {
            margin: 0;
            color: #E0E0E0;
            line-height: 1.6;
        }

        .card-strengths { border-left: 4px solid #6ABF1E; }
        .card-strengths h4 { color: #6ABF1E; }

        .card-weaknesses { border-left: 4px solid #FFA500; }
        .card-weaknesses h4 { color: #FFA500; }

        .card-feedback { border-left: 4px solid #4A9EFF; }
        .card-feedback h4 { color: #4A9EFF; }

        /* Score display */
        .score-display {
            background: linear-gradient(135deg, #1A1A1A, #2A2A2A);
            border: 2px solid #6ABF1E;
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            margin-bottom: 20px;
            box-shadow: 0 0 30px rgba(106,191,30,0.2);
            animation: pulse 2s ease-in-out;
        }

        .score-display .score-number {
            font-size: 4rem;
            font-weight: 900;
            color: #6ABF1E;
            line-height: 1;
        }

        .score-display .score-label {
            color: #AAAAAA;
            font-size: 0.9rem;
            margin-top: 4px;
        }

        .score-display .grade-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.9rem;
            margin-top: 12px;
        }

        .grade-pass { background: rgba(106,191,30,0.2); color: #6ABF1E; }
        .grade-borderline { background: rgba(255,165,0,0.2); color: #FFA500; }
        .grade-fail { background: rgba(255,80,80,0.2); color: #FF5050; }

        /* Divider */
        .ias-divider {
            border: none;
            border-top: 1px solid #3A3A3A;
            margin: 24px 0;
        }

        /* Footer */
        .ias-footer {
            text-align: center;
            color: #555;
            font-size: 0.78rem;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #2A2A2A;
        }

        /* Animations */
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(106,191,30,0.4); }
            70% { box-shadow: 0 0 0 20px rgba(106,191,30,0); }
            100% { box-shadow: 0 0 0 0 rgba(106,191,30,0); }
        }

        /* Spinner color */
        .stSpinner > div {
            border-top-color: #6ABF1E !important;
        }

        /* Warning and info */
        .stWarning {
            background-color: rgba(255,165,0,0.1) !important;
            border-color: #FFA500 !important;
            color: #FFA500 !important;
        }
    </style>
""", unsafe_allow_html=True)


# ── OpenAI client ─────────────────────────────────────────────────────────────

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)


# ── Google client ─────────────────────────────────────────────────────────────

def get_google_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"],
        scope
    )
    return gspread.authorize(creds)


# ── Functions ─────────────────────────────────────────────────────────────────

def grade_answer(student_answer):
    prompt = f"""
You are an academic tutor at the Institute of Accounting Science.

Grade the student's answer out of 100.

Return ONLY valid JSON.

Student Answer:
{student_answer}

JSON Format:

{{
    "score": 0,
    "strengths": [],
    "weaknesses": [],
    "feedback": ""
}}
"""
    response = client.responses.create(
        model="gpt-5",
        input=prompt
    )
    return json.loads(response.output_text)


def connect_sheet():
    gc = get_google_client()
    return gc.open("AI Tutor Results").sheet1


def get_random_scenario():
    gc = get_google_client()
    sheet = gc.open("AI Tutor Scenarios").sheet1
    rows = sheet.get_all_records()
    return random.choice(rows)


def log_submission(
    student_id, scenario_id, attempt,
    score, response, strengths, weaknesses, feedback
):
    sheet = connect_sheet()
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        student_id, scenario_id, attempt,
        score, response, strengths, weaknesses, feedback
    ])


# ── Session state ─────────────────────────────────────────────────────────────

if "scenario" not in st.session_state:
    st.session_state.scenario = get_random_scenario()

if "submitted" not in st.session_state:
    st.session_state.submitted = False


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
    <div class="ias-header">
        <h1>🎓 IAS AI Tutor</h1>
        <p>The Key To Success — Powered by Artificial Intelligence</p>
    </div>
""", unsafe_allow_html=True)


# ── Scenario ──────────────────────────────────────────────────────────────────

scenario = st.session_state.scenario

st.markdown(f"""
    <div class="scenario-box">
        <h3>📋 Scenario — {scenario["Title"]}</h3>
        <p>{scenario["Scenario"]}</p>
    </div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🔄 New"):
        st.session_state.scenario = get_random_scenario()
        st.session_state.submitted = False
        st.rerun()


# ── Input ─────────────────────────────────────────────────────────────────────

st.markdown('<div class="section-label">👤 Student ID</div>', unsafe_allow_html=True)
student_id = st.text_input("Student ID", label_visibility="collapsed")

st.markdown('<div class="section-label">✍️ Your Answer</div>', unsafe_allow_html=True)
answer = st.text_area(
    "Your Answer",
    placeholder="Type your answer here. Be thorough — the AI will assess your understanding, analysis, evidence and recommendations...",
    height=220,
    label_visibility="collapsed"
)

st.markdown('<hr class="ias-divider">', unsafe_allow_html=True)

if st.button("📤 Submit for AI Grading"):

    if not student_id:
        st.warning("⚠️ Please enter your Student ID before submitting.")

    elif not answer:
        st.warning("⚠️ Please write your answer before submitting.")

    else:
        with st.spinner("🤖 Analysing your answer..."):
            result = grade_answer(answer)
            score = result["score"]
            strengths = ", ".join(result["strengths"])
            weaknesses = ", ".join(result["weaknesses"])
            feedback = result["feedback"]

        # Grade badge
        if score >= 75:
            grade_class = "grade-pass"
            grade_label = "✅ Pass"
        elif score >= 50:
            grade_class = "grade-borderline"
            grade_label = "⚠️ Borderline"
        else:
            grade_class = "grade-fail"
            grade_label = "❌ Needs Work"

        # Score card
        st.markdown(f"""
            <div class="score-display">
                <div class="score-number">{score}</div>
                <div class="score-label">out of 100</div>
                <div class="grade-badge {grade_class}">{grade_label}</div>
            </div>
        """, unsafe_allow_html=True)

        # Result cards
        st.markdown(f"""
            <div class="result-card card-strengths">
                <h4>💪 Strengths</h4>
                <p>{strengths}</p>
            </div>
            <div class="result-card card-weaknesses">
                <h4>⚠️ Areas to Improve</h4>
                <p>{weaknesses}</p>
            </div>
            <div class="result-card card-feedback">
                <h4>💡 Tutor Feedback</h4>
                <p>{feedback}</p>
            </div>
        """, unsafe_allow_html=True)

        log_submission(
            student_id=student_id,
            scenario_id=scenario["ScenarioID"],
            attempt=1,
            score=score,
            response=answer,
            strengths=strengths,
            weaknesses=weaknesses,
            feedback=feedback
        )


# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("""
    <div class="ias-footer">
        Institute of Accounting Science · AI Tutor MVP · Confidential
    </div>
""", unsafe_allow_html=True)