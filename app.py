import streamlit as st
import json
from datetime import datetime
from docx import Document
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

st.set_page_config(page_title="AI Assessment", layout="centered")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ──────────────────────────────────────────────
# GOOGLE SHEETS
# ──────────────────────────────────────────────

def get_google_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    return gspread.authorize(creds)


def save_result(student_id, email, subject, scenario_id, score,
                response, strengths, weaknesses, feedback):
    """
    Logs to Google Sheet with columns:
    Timestamp | StudentID | Email | Subject | ScenarioID | Attempt |
    Score | Response | Strengths | Weaknesses | Feedback
    """
    try:
        gc = get_google_client()
        sheet = gc.open("AI Assessment Results").sheet1
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            student_id,
            email,
            subject,           # defaults to "Assessment" if not provided
            scenario_id,       # uses the uploaded filename
            1,                 # Attempt always 1 in this simple app
            score,
            response,
            strengths,
            weaknesses,
            feedback
        ])
    except Exception as e:
        st.warning(f"Result could not be saved to sheet: {e}")

# ──────────────────────────────────────────────
# DOCX PARSER
# ──────────────────────────────────────────────

def read_docx(uploaded_file):
    doc = Document(uploaded_file)
    return "\n".join(p.text for p in doc.paragraphs)


def split_document(content):
    """
    Splits the document into two parts using section markers.

    Expected format:
      [Any introductory text / scenario / question]
      === STUDENT SECTION ===
      [What students see and answer]
      === MARKER SECTION ===
      [Grading rubric / prompt instructions — NEVER shown to students]
    """
    STUDENT_MARKER = "=== STUDENT SECTION ==="
    MARKER_MARKER  = "=== MARKER SECTION ==="

    if STUDENT_MARKER not in content:
        raise ValueError("Document is missing the '=== STUDENT SECTION ===' marker.")
    if MARKER_MARKER not in content:
        raise ValueError("Document is missing the '=== MARKER SECTION ===' marker.")

    student_part = content.split(STUDENT_MARKER)[1].split(MARKER_MARKER)[0].strip()
    marker_part  = content.split(MARKER_MARKER)[1].strip()

    return student_part, marker_part

# ──────────────────────────────────────────────
# GRADING
# ──────────────────────────────────────────────

JSON_INSTRUCTION = (
    "\n\nIMPORTANT: Return ONLY valid JSON — no markdown, no code fences, no extra text.\n"
    "The JSON must contain exactly these four keys:\n"
    "  \"score\"     — percentage mark 0–100 (integer). "
    "If your rubric is out of a different total, convert to percentage first.\n"
    "  \"strengths\" — list of strings (what the student did well).\n"
    "  \"weaknesses\"— list of strings (what needs improvement).\n"
    "  \"feedback\"  — single string with detailed, criterion-by-criterion feedback.\n\n"
    "Example:\n"
    '{"score": 72, "strengths": ["Clear argument"], '
    '"weaknesses": ["Missing examples"], "feedback": "Good overall but..."}'
)


def _parse_result(raw: str) -> dict:
    """Safely parse the model response into the expected dict."""
    text = raw.strip()

    # Strip markdown code fences if the model added them anyway
    if text.startswith("```"):
        lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {
            "score": 0,
            "strengths": [],
            "weaknesses": [],
            "feedback": (
                "The grading engine could not parse a result for this submission. "
                "Please try again or contact your lecturer."
            )
        }

    # Normalise score
    try:
        score = float(data.get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    data["score"] = max(0, min(100, round(score)))

    # Normalise lists
    for key in ("strengths", "weaknesses"):
        if not isinstance(data.get(key), list):
            data[key] = []

    # Normalise feedback
    if not isinstance(data.get("feedback"), str):
        data["feedback"] = ""

    return data


def grade_answer(student_content, marker_content, student_answer) -> dict:
    """
    Builds the grading prompt from the MARKER SECTION of the uploaded docx,
    then calls the model and returns a parsed result dict.

    The marker_content is the full rubric/instructions from the document.
    It is never shown to the student — only used here as the grading prompt.
    """
    prompt = (
        "You are an academic marker.\n\n"
        "STUDENT CONTENT (what the student was shown):\n"
        f"{student_content}\n\n"
        "MARKING GUIDE (rubric and instructions from the document):\n"
        f"{marker_content}\n\n"
        "STUDENT ANSWER:\n"
        f"{student_answer}"
        + JSON_INSTRUCTION
    )

    response = client.responses.create(model="gpt-4o", input=prompt)
    return _parse_result(response.output_text.strip())

# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────

if "result" not in st.session_state:
    st.session_state.result = None

# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────

st.title("AI Assessment System")

# ── Document upload ────────────────────────────

uploaded_doc = st.file_uploader("Upload Assessment Document (.docx)", type=["docx"])

if not uploaded_doc:
    st.info("Please upload an assessment document to begin.")
    st.stop()

# Parse the document every time a new file is loaded
try:
    document_text = read_docx(uploaded_doc)
    student_content, marker_content = split_document(document_text)
except ValueError as e:
    st.error(str(e))
    st.stop()

# ── Assessment form ────────────────────────────

st.subheader("Assessment")

# Only the student section is displayed — marker section stays hidden
st.markdown(student_content)

st.divider()

student_id = st.text_input("Student Number")
email      = st.text_input("Email (optional)")
answer     = st.text_area("Your Answer", height=250)

submit = st.button("Submit")

# ── On submit ──────────────────────────────────

if submit:
    if not student_id.strip():
        st.warning("Please enter your Student Number before submitting.")
        st.stop()
    if not answer.strip():
        st.warning("Please write your answer before submitting.")
        st.stop()

    with st.spinner("Marking your answer..."):
        try:
            result = grade_answer(student_content, marker_content, answer)
        except Exception as e:
            st.error(f"Grading failed: {e}")
            st.stop()

    st.session_state.result = result

    # Save to Google Sheets — unused fields get sensible defaults
    save_result(
        student_id  = student_id.strip(),
        email       = email.strip(),
        subject     = "Assessment",          # no subject selector in this app
        scenario_id = uploaded_doc.name,     # filename acts as ScenarioID
        score       = result["score"],
        response    = answer.strip(),
        strengths   = ", ".join(result["strengths"]),
        weaknesses  = ", ".join(result["weaknesses"]),
        feedback    = result["feedback"]
    )

# ── Results ────────────────────────────────────

if st.session_state.result:
    r = st.session_state.result

    st.divider()
    st.subheader("Your Result")

    st.metric("Score", f"{r['score']} / 100")

    st.subheader("Feedback")
    st.write(r["feedback"])

    if r["strengths"]:
        st.subheader("Strengths")
        for item in r["strengths"]:
            st.write(f"• {item}")

    if r["weaknesses"]:
        st.subheader("Areas to Improve")
        for item in r["weaknesses"]:
            st.write(f"• {item}")