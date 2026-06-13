import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from openai import OpenAI
import json
import random

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

# ── Google client using Streamlit secrets ────────────────────────────────────

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


# ── All functions ────────────────────────────────────────────────────────────

def grade_answer(student_answer):

    prompt = f"""
You are an academic tutor.

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


# ── Session state ────────────────────────────────────────────────────────────

if "scenario" not in st.session_state:
    st.session_state.scenario = get_random_scenario()


# ── UI ───────────────────────────────────────────────────────────────────────

st.title("IAS AI Tutor")
scenario = st.session_state.scenario

st.subheader(
    scenario["Title"]
)

st.write(
    scenario["Scenario"]
)

student_id = st.text_input("Student ID")

answer = st.text_area(
    "Submit your answer"
)

if st.button("Load New Scenario"):
    st.session_state.scenario = get_random_scenario()
    st.rerun()

if st.button("Submit"):

    with st.spinner("Grading your answer..."):

        result = grade_answer(answer)
        score = result["score"]

        strengths = ", ".join(
            result["strengths"]
        )

        weaknesses = ", ".join(
            result["weaknesses"]
        )

        feedback = result["feedback"]
        st.success("Assessment Complete")

        st.metric(
            "Score",
            f"{score}/100"
        )

        st.subheader("Strengths")
        st.write(strengths)

        st.subheader("Weaknesses")
        st.write(weaknesses)

        st.subheader("Feedback")
        st.write(feedback)

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