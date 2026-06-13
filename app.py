import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from openai import OpenAI
import json
import random

# ── Branding ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IAS AI Tutor",
    page_icon="🎓",
    layout="centered"
)

st.markdown("""
    <style>
        /* Background */
        .stApp {
            background-color: #F9F9F9;
        }

        /* Header banner */
        .ias-header {
            background-color: #6ABF1E;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        }

        .ias-header h1 {
            color: white;
            font-size: 2rem;
            margin: 0;
        }

        .ias-header p {
            color: white;
            margin: 5px 0 0 0;
            font-size: 0.9rem;
        }

        /* Scenario box */
        .scenario-box {
            background-color: #1A1A1A;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 5px solid #6ABF1E;
        }

        .scenario-box h3 {
            color: #6ABF1E;
            margin-top: 0;
        }

        /* Buttons */
        .stButton > button {
            background-color: #6ABF1E;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: bold;
            width: 100%;
        }

        .stButton > button:hover {
            background-color: #58A015;
            color: white;
        }

        /* Score metric */
        .stMetric {
            background-color: #1A1A1A;
            border-radius: 10px;
            padding: 10px;
            color: white;
        }

        /* Success box */
        .stSuccess {
            background-color: #6ABF1E;
            color: white;
        }

        /* Text input and area */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            border: 2px solid #6ABF1E;
            border-radius: 8px;
        }

        /* Footer */
        .ias-footer {
            text-align: center;
            color: #999;
            font-size: 0.8rem;
            margin-top: 40px;
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


# ── All functions ─────────────────────────────────────────────────────────────

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

    return json.loads(
        response.output_text
    )


def connect_sheet():

    gc = get_google_client()

    return gc.open("AI Tutor Results").sheet1


def get_random_scenario():

    gc = get_google_client()

    sheet = gc.open(
        "AI Tutor Scenarios"
    ).sheet1

    rows = sheet.get_all_records()

    return random.choice(rows)


def log_submission(
    student_id,
    scenario_id,
    attempt,
    score,
    response,
    strengths,
    weaknesses,
    feedback
):

    sheet = connect_sheet()

    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        student_id,
        scenario_id,
        attempt,
        score,
        response,
        strengths,
        weaknesses,
        feedback
    ])


# ── Session state ─────────────────────────────────────────────────────────────

if "scenario" not in st.session_state:
    st.session_state.scenario = get_random_scenario()


# ── UI ────────────────────────────────────────────────────────────────────────

# Header
st.markdown("""
    <div class="ias-header">
        <h1>🎓 IAS AI Tutor</h1>
        <p>The Key To Success — Powered by Artificial Intelligence</p>
    </div>
""", unsafe_allow_html=True)

# Scenario box
scenario = st.session_state.scenario

st.markdown(f"""
    <div class="scenario-box">
        <h3>📋 {scenario["Title"]}</h3>
        <p>{scenario["Scenario"]}</p>
    </div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

with col2:
    if st.button("🔄 New Scenario"):
        st.session_state.scenario = get_random_scenario()
        st.rerun()

# Student input
st.markdown("### 👤 Your Details")
student_id = st.text_input("Student ID")

st.markdown("### ✍️ Your Answer")
answer = st.text_area(
    "Type your answer here...",
    height=200
)

st.markdown("---")

if st.button("📤 Submit for Grading"):

    if not student_id:
        st.warning("⚠️ Please enter your Student ID before submitting.")

    elif not answer:
        st.warning("⚠️ Please write your answer before submitting.")

    else:
        with st.spinner("🤖 AI is grading your answer..."):

            result = grade_answer(answer)
            score = result["score"]

            strengths = ", ".join(
                result["strengths"]
            )

            weaknesses = ", ".join(
                result["weaknesses"]
            )

            feedback = result["feedback"]

        st.success("✅ Assessment Complete!")

        # Score display
        st.markdown("### 📊 Your Results")

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                label="Your Score",
                value=f"{score}/100"
            )

        with col2:
            if score >= 75:
                st.metric(label="Grade", value="🟢 Pass")
            elif score >= 50:
                st.metric(label="Grade", value="🟡 Borderline")
            else:
                st.metric(label="Grade", value="🔴 Needs Work")

        st.markdown("### 💪 Strengths")
        st.success(strengths)

        st.markdown("### ⚠️ Weaknesses")
        st.warning(weaknesses)

        st.markdown("### 💡 Feedback")
        st.info(feedback)

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

# Footer
st.markdown("""
    <div class="ias-footer">
        Institute of Accounting Science — AI Tutor MVP
    </div>
""", unsafe_allow_html=True)