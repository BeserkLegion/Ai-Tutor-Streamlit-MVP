import streamlit as st
import json
from datetime import datetime
from pathlib import Path

from docx import Document
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI

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
    "MaxScore",
    "Response",
    "Strengths",
    "Weaknesses",
    "Feedback",
    "Improve",
]

ASSESSMENT_FILE = Path("current_assessment.docx")
RUBRIC_FILE = Path("current_rubric.json")


# ---------------------------------------------------------------------------
# Google Sheets helpers
# ---------------------------------------------------------------------------

def get_google_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    return gspread.authorize(credentials)


def get_results_sheet():
    gc = get_google_client()
    sheet = gc.open(SHEET_NAME).sheet1
    existing_headers = sheet.row_values(1)
    if not existing_headers:
        sheet.append_row(SHEET_HEADERS)
    elif existing_headers != SHEET_HEADERS:
        raise ValueError("Google Sheet headers must be: " + ", ".join(SHEET_HEADERS))
    return sheet


def get_attempt_number(sheet, student_id, scenario_id):
    try:
        records = sheet.get_all_records()
        previous = [
            r for r in records
            if str(r.get("StudentID", "")).strip() == student_id
            and str(r.get("ScenarioID", "")).strip() == scenario_id
        ]
        return len(previous) + 1
    except Exception:
        return 1


def save_result(student_id, email, subject, scenario_id, score, max_score,
                response, strengths, weaknesses, feedback, improve):
    try:
        sheet = get_results_sheet()
        attempt = get_attempt_number(sheet, student_id, scenario_id)
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            student_id, email, subject, scenario_id, attempt,
            score, max_score, response, strengths, weaknesses, feedback, improve,
        ])
    except Exception as error:
        st.warning(f"Result could not be saved: {error}")


# ---------------------------------------------------------------------------
# Document helpers
# ---------------------------------------------------------------------------

def read_docx(file_path_or_upload):
    document = Document(file_path_or_upload)
    return "\n".join(p.text for p in document.paragraphs)


def split_document(content):
    student_marker = "=== STUDENT SECTION ==="
    marker_marker = "=== MARKER SECTION ==="
    if student_marker not in content:
        raise ValueError("Document is missing the '=== STUDENT SECTION ===' marker.")
    if marker_marker not in content:
        raise ValueError("Document is missing the '=== MARKER SECTION ===' marker.")
    student_content = content.split(student_marker, 1)[1].split(marker_marker, 1)[0].strip()
    marker_content = content.split(marker_marker, 1)[1].strip()
    if not student_content:
        raise ValueError("The STUDENT SECTION is empty.")
    if not marker_content:
        raise ValueError("The MARKER SECTION is empty.")
    return student_content, marker_content


# ---------------------------------------------------------------------------
# Rubric extraction  (runs once at upload time, result cached as JSON)
# ---------------------------------------------------------------------------

RUBRIC_EXTRACTION_PROMPT = """
You are reading the MARKER SECTION of an assessment document.
Your job is to extract the scoring rubric structure from it.

Return ONLY valid JSON — no markdown, no backticks, no preamble.

The JSON must have this shape:
{
  "sections": [
    {
      "name": "Human-readable section name exactly as it appears in the rubric",
      "key":  "snake_case identifier (e.g. ethical_framework)",
      "max_marks": <integer — maximum marks for this section>,
      "criteria": [
        {
          "name": "Criterion name",
          "max_marks": <integer — max marks for this single criterion>
        }
      ]
    }
  ],
  "total_max": <integer — sum of all section max_marks>
}

Rules:
- Read the rubric carefully and extract every section and every criterion.
- "max_marks" for a section equals the sum of its criteria max_marks.
- "total_max" equals the sum of all section max_marks.
- Do NOT invent sections or criteria that are not in the document.
"""


def extract_rubric(marker_content: str) -> dict:
    """Call the LLM to parse the rubric structure from the marker section."""
    response = client.responses.create(
        model="gpt-4o",
        input=f"{RUBRIC_EXTRACTION_PROMPT}\n\nMARKER SECTION:\n{marker_content}",
    )
    text = response.output_text.strip()
    if text.startswith("```"):
        text = "\n".join(
            l for l in text.splitlines() if not l.strip().startswith("```")
        ).strip()
    rubric = json.loads(text)
    # Recalculate total_max from sections to be safe
    rubric["total_max"] = sum(s["max_marks"] for s in rubric["sections"])
    return rubric


def load_rubric() -> dict | None:
    if RUBRIC_FILE.exists():
        try:
            return json.loads(RUBRIC_FILE.read_text())
        except Exception:
            pass
    return None


def save_rubric(rubric: dict):
    RUBRIC_FILE.write_text(json.dumps(rubric, indent=2))


# ---------------------------------------------------------------------------
# Assessment loader
# ---------------------------------------------------------------------------

def load_current_assessment():
    if not ASSESSMENT_FILE.exists():
        return None, None, None, None
    try:
        document_text = read_docx(ASSESSMENT_FILE)
        student_content, marker_content = split_document(document_text)
        rubric = load_rubric()
        return student_content, marker_content, ASSESSMENT_FILE.name, rubric
    except Exception as error:
        st.error(f"Could not load the current assessment: {error}")
        return None, None, None, None


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def build_grading_prompt(student_content, marker_content, student_answer, rubric):
    sections_desc = "\n".join(
        f'  - "{s["name"]}" (key: "{s["key"]}", max {s["max_marks"]} marks, '
        f'{len(s["criteria"])} criteria worth '
        + ", ".join(f'{c["max_marks"]}' for c in s["criteria"])
        + " marks each)"
        for s in rubric["sections"]
    )
    section_score_keys = "\n".join(
        f'    "{s["key"]}": <integer 0–{s["max_marks"]}>'
        for s in rubric["sections"]
    )

    return f"""You are an academic marker.

STUDENT CONTENT:
{student_content}

MARKING GUIDE:
{marker_content}

STUDENT ANSWER:
{student_answer}

RUBRIC STRUCTURE (extracted from this document):
The rubric has {len(rubric["sections"])} sections with a total of {rubric["total_max"]} marks:
{sections_desc}

IMPORTANT: Return ONLY valid JSON — no markdown, no backticks, no preamble.

Score the student's answer strictly according to the rubric above.
For each criterion within a section, award 0, 1, … up to its max marks.
Sum criteria scores to get each section score; sum section scores for total_score.

The JSON must contain exactly these keys:

"section_scores" - object with one key per section:
{section_score_keys}
"total_score"    - integer 0–{rubric["total_max"]} (must equal sum of section_scores)
"strengths"      - list of strings (things the student did well)
"weaknesses"     - list of strings (areas that cost marks)
"feedback"       - detailed criterion-by-criterion feedback explaining every mark awarded
"improve"        - list of strings: one specific, actionable step per criterion not at full marks
"""


def parse_result(raw, rubric):
    text = raw.strip()
    if text.startswith("```"):
        text = "\n".join(
            l for l in text.splitlines() if not l.strip().startswith("```")
        ).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        empty_scores = {s["key"]: 0 for s in rubric["sections"]}
        return {
            "section_scores": empty_scores,
            "total_score": 0,
            "strengths": [],
            "weaknesses": [],
            "feedback": "The grading engine could not produce a valid result.",
            "improve": [],
        }

    # Validate and clamp each section score
    section_scores = data.get("section_scores", {})
    if not isinstance(section_scores, dict):
        section_scores = {}

    for s in rubric["sections"]:
        key = s["key"]
        try:
            section_scores[key] = max(0, min(s["max_marks"], round(float(section_scores.get(key, 0)))))
        except (TypeError, ValueError):
            section_scores[key] = 0

    data["section_scores"] = section_scores
    data["total_score"] = sum(section_scores[s["key"]] for s in rubric["sections"])

    for key in ("strengths", "weaknesses", "improve"):
        if not isinstance(data.get(key), list):
            data[key] = []

    if not isinstance(data.get("feedback"), str):
        data["feedback"] = ""

    return data


def grade_answer(student_content, marker_content, student_answer, rubric):
    prompt = build_grading_prompt(student_content, marker_content, student_answer, rubric)
    response = client.responses.create(model="gpt-4o", input=prompt)
    return parse_result(response.output_text, rubric)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "result" not in st.session_state:
    st.session_state.result = None

if "rubric" not in st.session_state:
    st.session_state.rubric = None


# ---------------------------------------------------------------------------
# Admin page
# ---------------------------------------------------------------------------

def admin_upload():
    st.title("Admin Upload")

    if not st.session_state.admin_authenticated:
        password = st.text_input("Admin Password", type="password")
        admin_password = st.secrets.get("ADMIN_PASSWORD", "")
        if st.button("Log In"):
            if not admin_password:
                st.error("Admin password has not been configured.")
            elif password == admin_password:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect admin password.")
        return

    uploaded_doc = st.file_uploader("Upload Assessment Document (.docx)", type=["docx"])

    if uploaded_doc:
        try:
            document_text = read_docx(uploaded_doc)
            student_content, marker_content = split_document(document_text)

            with st.spinner("Reading rubric structure from document…"):
                rubric = extract_rubric(marker_content)

            ASSESSMENT_FILE.write_bytes(uploaded_doc.getvalue())
            save_rubric(rubric)
            st.session_state.rubric = rubric

            st.success("Assessment uploaded successfully.")

            with st.expander("Student Section Preview"):
                st.markdown(student_content)

            with st.expander("Rubric Structure Detected"):
                for s in rubric["sections"]:
                    st.markdown(f"**{s['name']}** — {s['max_marks']} marks")
                    for c in s["criteria"]:
                        st.markdown(f"  - {c['name']} ({c['max_marks']} marks)")
                st.markdown(f"**Total: {rubric['total_max']} marks**")

            with st.expander("Marker Section Preview"):
                st.text(marker_content)

        except Exception as error:
            st.error(f"Upload failed: {error}")

    if st.button("Log Out"):
        st.session_state.admin_authenticated = False
        st.rerun()


# ---------------------------------------------------------------------------
# Student page
# ---------------------------------------------------------------------------

def student_assessment():
    st.title("AI Tutor")

    student_content, marker_content, scenario_id, rubric = load_current_assessment()

    if not student_content or not rubric:
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

        with st.spinner("Marking your answer…"):
            try:
                result = grade_answer(
                    student_content=student_content,
                    marker_content=marker_content,
                    student_answer=answer.strip(),
                    rubric=rubric,
                )
            except Exception as error:
                st.error(f"Grading failed: {error}")
                return

        save_result(
            student_id=student_id.strip(),
            email=email.strip(),
            subject="Assessment",
            scenario_id=scenario_id,
            score=result["total_score"],
            max_score=rubric["total_max"],
            response=answer.strip(),
            strengths=" | ".join(result["strengths"]),
            weaknesses=" | ".join(result["weaknesses"]),
            feedback=result["feedback"],
            improve=" | ".join(result["improve"]),
        )

        st.session_state.result = result
        st.session_state.rubric = rubric

    if st.session_state.result:
        result = st.session_state.result
        rubric = st.session_state.rubric
        scores = result["section_scores"]

        st.divider()
        st.subheader("Your Result")

        # Dynamic columns — one per section + one for total
        cols = st.columns(len(rubric["sections"]) + 1)
        for i, section in enumerate(rubric["sections"]):
            cols[i].metric(
                section["name"],
                f"{scores[section['key']]} / {section['max_marks']}"
            )
        cols[-1].metric("Total", f"{result['total_score']} / {rubric['total_max']}")

        st.subheader("Feedback")
        st.write(result["feedback"])

        if result["strengths"]:
            st.subheader("Strengths")
            for s in result["strengths"]:
                st.write(f"• {s}")

        if result["improve"] or result["weaknesses"]:
            st.subheader("Areas to Improve")
            for item in result["improve"] or result["weaknesses"]:
                st.write(f"• {item}")


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

page = st.sidebar.radio("Navigation", ["Student Assessment", "Admin Upload"])

if page == "Admin Upload":
    admin_upload()
else:
    student_assessment()