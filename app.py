import streamlit as st
import json
from datetime import datetime
from pathlib import Path

from docx import Document
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

st.set_page_config(page_title="AI Tutor", layout="centered")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

SHEET_NAME = "AI Tutor Results"

SHEET_HEADERS = [
    "Timestamp",
    "StudentID",
    "Email",
    "Subject",
    "ScenarioID",
    "Attempt",
    "Score",
    "Response",
    "Strengths",
    "Weaknesses",
]

ASSESSMENT_FILE = Path("current_assessment.docx")

# ──────────────────────────────────────────────
# GOOGLE SHEETS
# ──────────────────────────────────────────────

def get_google_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"],
        scope,
    )

    return gspread.authorize(credentials)


def get_results_sheet():
    gc = get_google_client()
    sheet = gc.open(SHEET_NAME).sheet1

    existing_headers = sheet.row_values(1)

    if not existing_headers:
        sheet.append_row(SHEET_HEADERS)
    elif existing_headers != SHEET_HEADERS:
        raise ValueError(
            "Google Sheet headers must be: "
            + ", ".join(SHEET_HEADERS)
        )

    return sheet


def get_attempt_number(sheet, student_id, scenario_id):
    try:
        records = sheet.get_all_records()

        previous_attempts = [
            row
            for row in records
            if str(row.get("StudentID", "")).strip() == student_id
            and str(row.get("ScenarioID", "")).strip() == scenario_id
        ]

        return len(previous_attempts) + 1
    except Exception:
        return 1


def save_result(
    student_id,
    email,
    subject,
    scenario_id,
    score,
    response,
    strengths,
    weaknesses,
):
    try:
        sheet = get_results_sheet()
        attempt = get_attempt_number(sheet, student_id, scenario_id)

        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            student_id,
            email,
            subject,
            scenario_id,
            attempt,
            score,
            response,
            strengths,
            weaknesses,
        ])
    except Exception as error:
        st.warning(f"Result could not be saved: {error}")


# ──────────────────────────────────────────────
# DOCX PARSER
# ──────────────────────────────────────────────

def read_docx(file_path_or_upload):
    document = Document(file_path_or_upload)
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def split_document(content):
    student_marker = "=== STUDENT SECTION ==="
    marker_marker = "=== MARKER SECTION ==="

    if student_marker not in content:
        raise ValueError(
            "Document is missing the '=== STUDENT SECTION ===' marker."
        )

    if marker_marker not in content:
        raise ValueError(
            "Document is missing the '=== MARKER SECTION ===' marker."
        )

    student_content = content.split(student_marker, 1)[1].split(marker_marker, 1)[0].strip()
    marker_content = content.split(marker_marker, 1)[1].strip()

    if not student_content:
        raise ValueError("The STUDENT SECTION is empty.")

    if not marker_content:
        raise ValueError("The MARKER SECTION is empty.")

    return student_content, marker_content


def load_current_assessment():
    if not ASSESSMENT_FILE.exists():
        return None, None, None

    try:
        document_text = read_docx(ASSESSMENT_FILE)
        student_content, marker_content = split_document(document_text)

        return student_content, marker_content, ASSESSMENT_FILE.name

    except Exception as error:
        st.error(f"Could not load the current assessment: {error}")
        return None, None, None


# ──────────────────────────────────────────────
# GRADING
# ──────────────────────────────────────────────

JSON_INSTRUCTION = """
IMPORTANT: Return ONLY valid JSON.

The JSON must contain exactly these keys:
"score"      - integer percentage from 0 to 100
"strengths"  - list of strings
"weaknesses" - list of strings
"feedback"   - detailed criterion-by-criterion feedback

Example:
{
  "score": 72,
  "strengths": ["Clear explanation"],
  "weaknesses": ["Missing legal analysis"],
  "feedback": "You identified the ethical issue, but..."
}
"""


def parse_result(raw):
    text = raw.strip()

    if text.startswith("```"):
        lines = [
            line
            for line in text.splitlines()
            if not line.strip().startswith("```")
        ]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {
            "score": 0,
            "strengths": [],
            "weaknesses": [],
            "feedback": "The grading engine could not produce a valid result.",
        }

    try:
        score = float(data.get("score", 0))
    except (TypeError, ValueError):
        score = 0

    data["score"] = max(0, min(100, round(score)))

    for key in ("strengths", "weaknesses"):
        if not isinstance(data.get(key), list):
            data[key] = []

    if not isinstance(data.get("feedback"), str):
        data["feedback"] = ""

    return data


def grade_answer(student_content, marker_content, student_answer):
    prompt = f"""
You are an academic marker.

STUDENT CONTENT:
{student_content}

MARKING GUIDE:
{marker_content}

STUDENT ANSWER:
{student_answer}

{JSON_INSTRUCTION}
"""

    response = client.responses.create(
        model="gpt-4o",
        input=prompt,
    )

    return parse_result(response.output_text)


# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "result" not in st.session_state:
    st.session_state.result = None


# ──────────────────────────────────────────────
# ADMIN UPLOAD
# ──────────────────────────────────────────────

def admin_upload():
    st.title("Admin Upload")

    if not st.session_state.admin_authenticated:
        password = st.text_input("Admin Password", type="password")

        if st.button("Log In"):
            if password == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect admin password.")

        return

    uploaded_doc = st.file_uploader(
        "Upload Assessment Document (.docx)",
        type=["docx"],
    )

    if uploaded_doc:
        try:
            document_text = read_docx(uploaded_doc)
            student_content, marker_content = split_document(document_text)

            ASSESSMENT_FILE.write_bytes(uploaded_doc.getvalue())

            st.success("Assessment uploaded successfully.")

            with st.expander("Student Section Preview"):
                st.markdown(student_content)

            with st.expander("Marker Section Preview"):
                st.text(marker_content)

        except Exception as error:
            st.error(f"Upload failed: {error}")

    if st.button("Log Out"):
        st.session_state.admin_authenticated = False
        st.rerun()


# ──────────────────────────────────────────────
# STUDENT VIEW
# ──────────────────────────────────────────────

def student_assessment():
    st.title("AI Tutor")

    student_content, marker_content, scenario_id = load_current_assessment()

    if not student_content:
        st.info("No assessment is currently available.")
        return

    st.subheader("Assessment")
    st.markdown(student_content)

    st.divider()

    student_id = st.text_input("Student Number")
    email = st.text_input("Email")
    answer = st.text_area("Your Answer", height=250)

    if st.button("Submit Answer", type="primary"):
        if not student_id.strip():
            st.warning("Please enter your Student Number.")
            return

        if not answer.strip():
            st.warning("Please write your answer.")
            return

        with st.spinner("Marking your answer..."):
            try:
                result = grade_answer(
                    student_content=student_content,
                    marker_content=marker_content,
                    student_answer=answer.strip(),
                )
            except Exception as error:
                st.error(f"Grading failed: {error}")
                return

        save_result(
            student_id=student_id.strip(),
            email=email.strip(),
            subject="Assessment",
            scenario_id=scenario_id,
            score=result["score"],
            response=answer.strip(),
            strengths=" | ".join(result["strengths"]),
            weaknesses=" | ".join(result["weaknesses"]),
        )

        st.session_state.result = result

    if st.session_state.result:
        result = st.session_state.result

        st.divider()
        st.subheader("Your Result")

        st.metric("Score", f"{result['score']} / 100")

        st.subheader("Feedback")
        st.write(result["feedback"])

        if result["strengths"]:
            st.subheader("Strengths")
            for strength in result["strengths"]:
                st.write(f"• {strength}")

        if result["weaknesses"]:
            st.subheader("Areas to Improve")
            for weakness in result["weaknesses"]:
                st.write(f"• {weakness}")


# ──────────────────────────────────────────────
# APP NAVIGATION
# ──────────────────────────────────────────────

page = st.sidebar.radio(
    "Navigation",
    ["Student Assessment", "Admin Upload"],
)

if page == "Admin Upload":
    admin_upload()
else:
    student_assessment()