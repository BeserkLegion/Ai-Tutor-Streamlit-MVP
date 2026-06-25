import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)).replace("/pages", ""))

import streamlit as st
from utils import read_docx, split_document, extract_rubric, save_rubric, ASSESSMENT_FILE

st.set_page_config(page_title="Admin Upload", layout="centered")

st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False


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


admin_upload()