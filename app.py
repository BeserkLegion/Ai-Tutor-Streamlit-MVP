import streamlit as st
from utils import load_current_assessment, grade_answer, save_result

st.set_page_config(page_title="AI Tutor", layout="centered")

if "result" not in st.session_state:
    st.session_state.result = None

if "rubric" not in st.session_state:
    st.session_state.rubric = None


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


student_assessment()