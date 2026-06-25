import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from utils import load_current_assessment, grade_answer, save_result

st.set_page_config(page_title="AI Tutor", layout="centered")

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
for key, default in {
    "result": None,
    "rubric": None,
    "admin_authenticated": False,
    "marking_in_progress": False,
    "pending_answer": None,
    "pending_student_id": None,
    "pending_email": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------------------------
# Sidebar — locked while marking
# ---------------------------------------------------------------------------
with st.sidebar:
    if st.session_state.marking_in_progress:
        st.warning("⏳ Marking in progress — navigation is disabled.")
        page = "Student Assessment"
    else:
        page = st.radio("Navigation", ["Student Assessment", "Admin"])


# ---------------------------------------------------------------------------
# Student page
# ---------------------------------------------------------------------------
def student_assessment():
    st.title("AI Tutor")

    student_content, marker_content, scenario_id, rubric = load_current_assessment()

    if not student_content or not rubric:
        st.info("No assessment is currently available.")
        return

    # Run marking if we have a pending submission
    if st.session_state.marking_in_progress and st.session_state.pending_answer:
        with st.spinner("Marking your answer… please do not navigate away."):
            try:
                result = grade_answer(
                    student_content=student_content,
                    marker_content=marker_content,
                    student_answer=st.session_state.pending_answer,
                    rubric=rubric,
                )
                save_result(
                    student_id=st.session_state.pending_student_id,
                    email=st.session_state.pending_email,
                    subject="Assessment",
                    scenario_id=scenario_id,
                    score=result["total_score"],
                    max_score=rubric["total_max"],
                    response=st.session_state.pending_answer,
                    strengths=" | ".join(result["strengths"]),
                    weaknesses=" | ".join(result["weaknesses"]),
                    feedback=result["feedback"],
                    improve=" | ".join(result["improve"]),
                )
                st.session_state.result = result
                st.session_state.rubric = rubric
            except Exception as error:
                st.error(f"Grading failed: {error}")
            finally:
                st.session_state.marking_in_progress = False
                st.session_state.pending_answer = None
                st.session_state.pending_student_id = None
                st.session_state.pending_email = None
        st.rerun()

    # Show result if available
    if st.session_state.result:
        result = st.session_state.result
        rubric = st.session_state.rubric
        scores = result["section_scores"]

        st.divider()
        st.subheader("Your Result")

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

        if st.button("Start New Attempt"):
            st.session_state.result = None
            st.session_state.rubric = None
            st.rerun()

        return

    # Submission form
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

        # Store submission in session state then rerun into the marking block
        st.session_state.pending_answer = answer.strip()
        st.session_state.pending_student_id = student_id.strip()
        st.session_state.pending_email = email.strip()
        st.session_state.marking_in_progress = True
        st.rerun()


# ---------------------------------------------------------------------------
# Admin page
# ---------------------------------------------------------------------------
def admin_page():
    st.title("Admin")

    if not st.session_state.admin_authenticated:
        st.subheader("Login")
        password = st.text_input("Admin Password", type="password")
        admin_password = st.secrets.get("ADMIN_PASSWORD", "")

        if st.button("Log In"):
            if not admin_password:
                st.error("Admin password has not been configured.")
            elif password == admin_password:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        return

    from utils import read_docx, split_document, extract_rubric, save_rubric, ASSESSMENT_FILE

    uploaded_doc = st.file_uploader("Upload Assessment Document (.docx)", type=["docx"])

    if uploaded_doc:
        try:
            document_text = read_docx(uploaded_doc)
            student_content, marker_content = split_document(document_text)

            with st.spinner("Reading rubric structure from document…"):
                rubric = extract_rubric(marker_content)

            ASSESSMENT_FILE.write_bytes(uploaded_doc.getvalue())
            save_rubric(rubric)

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
# Router
# ---------------------------------------------------------------------------
if page == "Admin":
    admin_page()
else:
    student_assessment()