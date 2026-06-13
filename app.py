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

        /* Dark metallic background */
        .stApp {
            background: linear-gradient(160deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
        }

        /* Hide streamlit default header */
        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* Remove red error outlines globally */
        .stTextInput > div > div > input:invalid,
        .stTextArea > div > div > textarea:invalid {
            box-shadow: none !important;
            border-color: #3A3A3A !important;
        }

        /* Remove streamlit default focus red */
        .stTextInput > div[data-focused="true"] > div,
        .stTextArea > div[data-focused="true"] > div {
            border-color: #6ABF1E !important;
            box-shadow: none !important;
        }

        /* Animated metallic header */
        .ias-header {
            background: linear-gradient(
                135deg,
                #3a7a0a 0%,
                #6ABF1E 30%,
                #8fd44e 50%,
                #6ABF1E 70%,
                #3a7a0a 100%
            );
            background-size: 200% auto;
            animation: shimmer 4s linear infinite, fadeInDown 0.6s ease;
            padding: 32px 20px;
            border-radius: 16px;
            text-align: center;
            margin-bottom: 24px;
            box-shadow:
                0 8px 32px rgba(106, 191, 30, 0.4),
                inset 0 1px 0 rgba(255,255,255,0.2),
                inset 0 -1px 0 rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.15);
        }

        .ias-header h1 {
            color: white;
            font-size: 2.4rem;
            font-weight: 900;
            margin: 0;
            letter-spacing: -0.5px;
            text-shadow: 0 2px 8px rgba(0,0,0,0.4);
        }

        .ias-header p {
            color: rgba(255,255,255,0.9);
            margin: 8px 0 0 0;
            font-size: 1rem;
            text-shadow: 0 1px 4px rgba(0,0,0,0.3);
        }

        /* Metallic scenario card */
        .scenario-box {
            background: linear-gradient(
                145deg,
                #2a2a2a 0%,
                #333333 40%,
                #2a2a2a 100%
            );
            border: 1px solid rgba(255,255,255,0.08);
            border-left: 5px solid #6ABF1E;
            padding: 24px;
            border-radius: 14px;
            margin-bottom: 24px;
            box-shadow:
                0 8px 32px rgba(0,0,0,0.4),
                inset 0 1px 0 rgba(255,255,255,0.05);
            animation: fadeInUp 0.5s ease;
        }

        .scenario-box h3 {
            color: #6ABF1E;
            margin-top: 0;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0 0 12px rgba(106,191,30,0.5);
        }

        .scenario-box p {
            color: #D0D0D0;
            line-height: 1.8;
            font-size: 0.95rem;
            margin: 0;
        }

        /* Section labels */
        .section-label {
            color: #6ABF1E;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 6px;
            text-shadow: 0 0 8px rgba(106,191,30,0.4);
        }

        /* Required badge */
        .required-badge {
            display: inline-block;
            background: rgba(106,191,30,0.15);
            color: #6ABF1E;
            font-size: 0.65rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 20px;
            border: 1px solid rgba(106,191,30,0.3);
            margin-left: 8px;
            vertical-align: middle;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        /* White metallic text inputs */
        .stTextInput > div > div > input {
            background: linear-gradient(
                145deg,
                #ffffff 0%,
                #f5f5f5 100%
            ) !important;
            color: #1A1A1A !important;
            border: 2px solid #444 !important;
            border-radius: 10px !important;
            font-size: 1rem !important;
            padding: 10px 14px !important;
            box-shadow:
                inset 0 2px 4px rgba(0,0,0,0.1),
                0 1px 0 rgba(255,255,255,0.05) !important;
            transition: all 0.3s ease !important;
            outline: none !important;
        }

        .stTextInput > div > div > input:focus {
            border-color: #6ABF1E !important;
            box-shadow:
                0 0 0 3px rgba(106,191,30,0.25),
                0 0 20px rgba(106,191,30,0.15),
                inset 0 2px 4px rgba(0,0,0,0.1) !important;
            outline: none !important;
        }

        /* Remove ALL red outlines on text input */
        .stTextInput > div > div > input:focus-visible {
            outline: none !important;
            border-color: #6ABF1E !important;
        }

        /* White metallic text area */
        .stTextArea > div > div > textarea {
            background: linear-gradient(
                145deg,
                #ffffff 0%,
                #f5f5f5 100%
            ) !important;
            color: #1A1A1A !important;
            border: 2px solid #444 !important;
            border-radius: 10px !important;
            font-size: 0.95rem !important;
            line-height: 1.7 !important;
            box-shadow:
                inset 0 2px 4px rgba(0,0,0,0.1) !important;
            transition: all 0.3s ease !important;
            outline: none !important;
        }

        .stTextArea > div > div > textarea:focus {
            border-color: #6ABF1E !important;
            box-shadow:
                0 0 0 3px rgba(106,191,30,0.25),
                0 0 20px rgba(106,191,30,0.15),
                inset 0 2px 4px rgba(0,0,0,0.1) !important;
            outline: none !important;
        }

        .stTextArea > div > div > textarea:focus-visible {
            outline: none !important;
            border-color: #6ABF1E !important;
        }

        /* Input labels */
        .stTextInput label,
        .stTextArea label {
            color: #888 !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
        }

        /* Metallic button */
        .stButton > button {
            background: linear-gradient(
                135deg,
                #4a9010 0%,
                #6ABF1E 40%,
                #8fd44e 60%,
                #6ABF1E 80%,
                #4a9010 100%
            ) !important;
            background-size: 200% auto !important;
            color: white !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            border-radius: 10px !important;
            padding: 12px 24px !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
            box-shadow:
                0 4px 15px rgba(106,191,30,0.4),
                inset 0 1px 0 rgba(255,255,255,0.2) !important;
            text-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
            animation: shimmer 3s linear infinite !important;
        }

        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow:
                0 8px 30px rgba(106,191,30,0.5),
                inset 0 1px 0 rgba(255,255,255,0.2) !important;
        }

        .stButton > button:active {
            transform: translateY(0px) !important;
        }

        /* Metallic score display */
        .score-display {
            background: linear-gradient(
                145deg,
                #1a1a1a 0%,
                #2a2a2a 50%,
                #1a1a1a 100%
            );
            border: 2px solid #6ABF1E;
            border-radius: 16px;
            padding: 28px;
            text-align: center;
            margin-bottom: 20px;
            box-shadow:
                0 0 40px rgba(106,191,30,0.3),
                inset 0 1px 0 rgba(255,255,255,0.05);
            animation: scoreReveal 0.6s ease, pulse 2s ease-in-out;
        }

        .score-number {
            font-size: 5rem;
            font-weight: 900;
            background: linear-gradient(135deg, #6ABF1E, #8fd44e, #6ABF1E);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1;
            text-shadow: none;
        }

        .score-label {
            color: #888;
            font-size: 0.9rem;
            margin-top: 4px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .grade-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.95rem;
            margin-top: 14px;
            letter-spacing: 0.5px;
        }

        .grade-pass {
            background: rgba(106,191,30,0.15);
            color: #6ABF1E;
            border: 1px solid rgba(106,191,30,0.4);
            box-shadow: 0 0 15px rgba(106,191,30,0.2);
        }

        .grade-borderline {
            background: rgba(255,165,0,0.15);
            color: #FFA500;
            border: 1px solid rgba(255,165,0,0.4);
            box-shadow: 0 0 15px rgba(255,165,0,0.2);
        }

        .grade-fail {
            background: rgba(255,80,80,0.15);
            color: #FF5050;
            border: 1px solid rgba(255,80,80,0.4);
            box-shadow: 0 0 15px rgba(255,80,80,0.2);
        }

        /* Metallic result cards */
        .result-card {
            background: linear-gradient(
                145deg,
                #252525 0%,
                #2f2f2f 100%
            );
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 14px;
            animation: fadeInUp 0.4s ease;
            box-shadow:
                0 4px 20px rgba(0,0,0,0.3),
                inset 0 1px 0 rgba(255,255,255,0.04);
        }

        .result-card h4 {
            margin: 0 0 10px 0;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 700;
        }

        .result-card p {
            margin: 0;
            color: #D0D0D0;
            line-height: 1.7;
            font-size: 0.93rem;
        }

        .card-strengths {
            border-left: 4px solid #6ABF1E;
        }
        .card-strengths h4 {
            color: #6ABF1E;
            text-shadow: 0 0 10px rgba(106,191,30,0.4);
        }

        .card-weaknesses {
            border-left: 4px solid #FFA500;
        }
        .card-weaknesses h4 {
            color: #FFA500;
            text-shadow: 0 0 10px rgba(255,165,0,0.4);
        }

        .card-feedback {
            border-left: 4px solid #4A9EFF;
        }
        .card-feedback h4 {
            color: #4A9EFF;
            text-shadow: 0 0 10px rgba(74,158,255,0.4);
        }

        /* Divider */
        .ias-divider {
            border: none;
            border-top: 1px solid #2A2A2A;
            margin: 24px 0;
        }

        /* Footer */
        .ias-footer {
            text-align: center;
            color: #444;
            font-size: 0.78rem;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #2A2A2A;
            letter-spacing: 1px;
        }

        /* Warning override */
        div[data-testid="stAlert"] {
            background: rgba(255,165,0,0.08) !important;
            border: 1px solid rgba(255,165,0,0.3) !important;
            border-radius: 10px !important;
            color: #FFA500 !important;
        }

        /* Spinner */
        .stSpinner > div {
            border-top-color: #6ABF1E !important;
        }

        /* Animations */
        @keyframes shimmer {
            0% { background-position: 200% center; }
            100% { background-position: -200% center; }
        }

        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes scoreReveal {
            from { opacity: 0; transform: scale(0.8); }
            to { opacity: 1; transform: scale(1); }
        }

        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(106,191,30,0.4); }
            70% { box-shadow: 0 0 0 20px rgba(106,191,30,0); }
            100% { box-shadow: 0 0 0 0 rgba(106,191,30,0); }
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

col1, col2 = st.columns([5, 1])
with col2:
    if st.button("🔄 New"):
        st.session_state.scenario = get_random_scenario()
        st.session_state.submitted = False
        st.rerun()


# ── Inputs ────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="section-label">👤 Student Number <span class="required-badge">Required</span></div>',
    unsafe_allow_html=True
)
student_id = st.text_input(
    "Student Number",
    placeholder="e.g. 20222526",
    label_visibility="collapsed"
)

st.markdown(
    '<div class="section-label">✍️ Your Answer</div>',
    unsafe_allow_html=True
)
answer = st.text_area(
    "Your Answer",
    placeholder="Type your answer here. Be thorough — the AI will assess your understanding, analysis, evidence and recommendations...",
    height=220,
    label_visibility="collapsed"
)

st.markdown('<hr class="ias-divider">', unsafe_allow_html=True)

if st.button("📤 Submit for AI Grading"):

    if not student_id.strip():
        st.warning("⚠️ Student Number is required before submitting.")

    elif not answer.strip():
        st.warning("⚠️ Please write your answer before submitting.")

    else:
        with st.spinner("🤖 Analysing your answer..."):
            result = grade_answer(answer)
            score = result["score"]
            strengths = ", ".join(result["strengths"])
            weaknesses = ", ".join(result["weaknesses"])
            feedback = result["feedback"]

        if score >= 75:
            grade_class = "grade-pass"
            grade_label = "✅ Pass"
        elif score >= 50:
            grade_class = "grade-borderline"
            grade_label = "⚠️ Borderline"
        else:
            grade_class = "grade-fail"
            grade_label = "❌ Needs Work"

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
        INSTITUTE OF ACCOUNTING SCIENCE · AI TUTOR MVP · CONFIDENTIAL
    </div>
""", unsafe_allow_html=True)