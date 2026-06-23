import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from openai import OpenAI
import json
import hashlib

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IAS AI Tutor",
    page_icon="🎓",
    layout="centered"
)

# ── Styling ────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; box-sizing: border-box; }

    .stApp {
        background: #000000;
        min-height: 100vh;
    }

    header[data-testid="stHeader"] { background: transparent; }

    /* ── Shared button reset ── */
    .stButton > button {
        background: #000 !important;
        color: #ffffff !important;
        border-radius: 4px !important;
        font-size: 1.3rem !important;
        font-weight: 400 !important;
        letter-spacing: 0.3px !important;
        transition: opacity 0.15s ease !important;
        box-shadow: none !important;
        text-transform: none !important;
        padding: 52px 16px !important;
        width: 100% !important;
        border: 2px solid transparent !important;
    }

    .stButton > button:hover { opacity: 0.8 !important; background: #0d0d0d !important; }
    .stButton > button:active { opacity: 0.6 !important; }
    .stButton > button:focus { outline: none !important; box-shadow: none !important; }

    div[data-testid="column"]:nth-of-type(1) div[data-testid="stButton"]:nth-of-type(1) > button {
        background:
            linear-gradient(#000, #000) padding-box,
            linear-gradient(135deg, #000000 0%, #00cfff 100%) border-box !important;
    }
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stButton"]:nth-of-type(1) > button {
        background:
            linear-gradient(#000, #000) padding-box,
            linear-gradient(135deg, #000000 0%, #9b30ff 100%) border-box !important;
    }
    div[data-testid="column"]:nth-of-type(1) div[data-testid="stButton"]:nth-of-type(2) > button {
        background:
            linear-gradient(#000, #000) padding-box,
            linear-gradient(135deg, #000000 0%, #ff2dd4 100%) border-box !important;
    }
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stButton"]:nth-of-type(2) > button {
        background:
            linear-gradient(#000, #000) padding-box,
            linear-gradient(135deg, #000000 0%, #00e676 100%) border-box !important;
    }

    .integrated-btn > div[data-testid="stButton"] > button {
        padding: 28px 16px !important;
        font-size: 1.3rem !important;
        background:
            linear-gradient(#000, #000) padding-box,
            linear-gradient(90deg, #000000 0%, #1a3aff 100%) border-box !important;
    }

    /* ── Login screen ── */
    .login-title {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 700;
        text-align: center;
        margin: 48px 0 6px 0;
        letter-spacing: 0.5px;
    }

    .login-subtitle {
        color: #888888;
        font-size: 0.88rem;
        text-align: center;
        margin: 0 0 40px 0;
    }

    .login-btn > div[data-testid="stButton"] > button {
        background:
            linear-gradient(#000, #000) padding-box,
            linear-gradient(90deg, #00eaff, #7b2fff) border-box !important;
        padding: 14px 16px !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }

    .login-btn > div[data-testid="stButton"] > button:hover {
        opacity: 0.85 !important;
    }

    /* ── Home title ── */
    .home-title {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 600;
        text-align: center;
        margin: 40px 0 32px 0;
        letter-spacing: 0.5px;
    }

    /* ── User badge ── */
    .user-badge {
        color: #888;
        font-size: 0.78rem;
        text-align: center;
        margin-bottom: 20px;
        letter-spacing: 0.3px;
    }

    .user-badge span {
        color: #00cfff;
        font-weight: 600;
    }

    /* ── Task list screen ── */
    .screen-title {
        color: #ffffff;
        font-size: 1.2rem;
        font-weight: 600;
        text-align: center;
        border: 1px solid #ffffff;
        border-radius: 4px;
        padding: 14px 20px;
        margin: 32px auto 24px auto;
        max-width: 520px;
    }

    .more-tasks-note {
        background: #000;
        border-radius: 4px;
        padding: 18px 20px;
        margin: 0 auto 12px auto;
        max-width: 520px;
        text-align: center;
        color: #aaaaaa;
        font-size: 0.9rem;
        border: 1.5px solid transparent;
        position: relative;
    }

    .more-tasks-note::before {
        content: "";
        position: absolute;
        inset: -1.5px;
        border-radius: 4px;
        padding: 1.5px;
        background: linear-gradient(90deg, #00eaff, #7b2fff);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: destination-out;
        mask-composite: exclude;
        pointer-events: none;
    }

    .task-list-btn > div[data-testid="stButton"] > button {
        background: #000 !important;
        border: 1.5px solid transparent !important;
        background-image:
            linear-gradient(#000, #000),
            linear-gradient(90deg, #00eaff, #7b2fff) !important;
        background-origin: border-box !important;
        background-clip: padding-box, border-box !important;
        padding: 18px 20px !important;
        font-size: 0.95rem !important;
        font-weight: 400 !important;
        text-align: left !important;
        line-height: 1.6 !important;
    }

    .nav-btn > div[data-testid="stButton"] > button {
        background: transparent !important;
        border: 1px solid #333 !important;
        color: #888 !important;
        padding: 8px 16px !important;
        font-size: 0.85rem !important;
        font-weight: 400 !important;
        width: auto !important;
    }

    .nav-btn > div[data-testid="stButton"] > button:hover {
        border-color: #555 !important;
        color: #ccc !important;
        background: transparent !important;
        opacity: 1 !important;
    }

    /* Sign out button — small, top-right feel */
    .signout-btn > div[data-testid="stButton"] > button {
        background: transparent !important;
        border: 1px solid #2a2a2a !important;
        color: #555 !important;
        padding: 6px 14px !important;
        font-size: 0.75rem !important;
        font-weight: 400 !important;
        width: auto !important;
        letter-spacing: 0.5px !important;
        text-transform: uppercase !important;
    }

    .signout-btn > div[data-testid="stButton"] > button:hover {
        border-color: #555 !important;
        color: #aaa !important;
        background: transparent !important;
        opacity: 1 !important;
    }

    /* ── Answer screen ── */
    .answer-header {
        color: #ffffff;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 28px 0 6px 0;
    }

    .answer-body {
        color: #cccccc;
        font-size: 0.92rem;
        line-height: 1.7;
        margin-bottom: 20px;
    }

    .field-label {
        color: #ffffff;
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 6px;
    }

    .stTextInput > div > div > input {
        background: #000000 !important;
        color: #ffffff !important;
        border: 1.5px solid transparent !important;
        border-radius: 4px !important;
        font-size: 0.95rem !important;
        padding: 10px 14px !important;
        outline: none !important;
        background-image: linear-gradient(#000, #000),
                          linear-gradient(90deg, #00eaff, #7b2fff) !important;
        background-origin: border-box !important;
        background-clip: padding-box, border-box !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    .stTextInput label,
    .stTextArea label { display: none !important; }

    .stTextArea > div > div > textarea {
        background: #000000 !important;
        color: #ffffff !important;
        border: 1.5px solid transparent !important;
        border-radius: 4px !important;
        font-size: 0.92rem !important;
        line-height: 1.7 !important;
        padding: 12px 14px !important;
        outline: none !important;
        background-image: linear-gradient(#000, #000),
                          linear-gradient(90deg, #00eaff, #7b2fff) !important;
        background-origin: border-box !important;
        background-clip: padding-box, border-box !important;
    }

    .stTextArea > div > div > textarea:focus {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    .submit-btn > div[data-testid="stButton"] > button {
        background: #5cb800 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 12px 40px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
        width: auto !important;
        display: block !important;
        margin: 0 auto !important;
    }

    .submit-btn > div[data-testid="stButton"] > button:hover {
        background: #4aa000 !important;
        opacity: 1 !important;
    }

    /* ── Result cards ── */
    .score-display {
        border: 1.5px solid transparent;
        border-radius: 6px;
        padding: 24px;
        text-align: center;
        margin-bottom: 20px;
        background-image: linear-gradient(#000, #000),
                          linear-gradient(90deg, #00eaff, #7b2fff);
        background-origin: border-box;
        background-clip: padding-box, border-box;
    }

    .score-number {
        font-size: 4rem;
        font-weight: 700;
        color: #5cb800;
        line-height: 1;
    }

    .score-label {
        color: #888;
        font-size: 0.82rem;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .grade-badge {
        display: inline-block;
        padding: 6px 18px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.88rem;
        margin-top: 12px;
    }

    .grade-pass       { background: rgba(92,184,0,0.12);  color: #5cb800; border: 1px solid rgba(92,184,0,0.35); }
    .grade-borderline { background: rgba(255,165,0,0.12); color: #FFA500; border: 1px solid rgba(255,165,0,0.35); }
    .grade-fail       { background: rgba(255,80,80,0.12); color: #FF5050; border: 1px solid rgba(255,80,80,0.35); }

    .result-card {
        border-radius: 6px;
        padding: 18px 20px;
        margin-bottom: 12px;
        background: #0d0d0d;
    }

    .result-card h4 {
        margin: 0 0 8px 0;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 700;
    }

    .result-card p {
        margin: 0;
        color: #cccccc;
        line-height: 1.7;
        font-size: 0.9rem;
    }

    .card-strengths  { border-left: 3px solid #5cb800; }
    .card-strengths h4 { color: #5cb800; }
    .card-weaknesses { border-left: 3px solid #FFA500; }
    .card-weaknesses h4 { color: #FFA500; }
    .card-feedback   { border-left: 3px solid #4A9EFF; }
    .card-feedback h4 { color: #4A9EFF; }

    .result-nav > div[data-testid="stButton"] > button {
        background: #000 !important;
        border: 1px solid #333 !important;
        color: #aaa !important;
        padding: 10px 16px !important;
        font-size: 0.88rem !important;
        font-weight: 400 !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
    }

    .result-nav > div[data-testid="stButton"] > button:hover {
        border-color: #555 !important;
        color: #fff !important;
        background: #0d0d0d !important;
        opacity: 1 !important;
    }

    .ias-footer {
        text-align: center;
        color: #333;
        font-size: 0.72rem;
        margin-top: 48px;
        padding-top: 16px;
        border-top: 1px solid #1a1a1a;
        letter-spacing: 1px;
    }

    .stSpinner > div { border-top-color: #5cb800 !important; }

    div[data-testid="stAlert"] {
        background: rgba(255,165,0,0.06) !important;
        border: 1px solid rgba(255,165,0,0.25) !important;
        border-radius: 6px !important;
        color: #FFA500 !important;
    }

    /* Error alert — red tint */
    div[data-testid="stAlert"][data-baseweb="notification"] {
        background: rgba(255,80,80,0.06) !important;
        border: 1px solid rgba(255,80,80,0.25) !important;
        color: #FF5050 !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Clients ────────────────────────────────────────────────────────────────────

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def get_google_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    return gspread.authorize(creds)


# ── Auth helpers ───────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.strip().encode()).hexdigest()


@st.cache_data(ttl=300)
def load_users():
    """Load users by column index to avoid gspread header-parsing bugs.
    Sheet column order must be: A=Email  B=Password  C=Name  D=Active"""
    gc = get_google_client()
    all_rows = gc.open("AI Tutor Users").sheet1.get_all_values()
    if len(all_rows) < 2:
        return []
    users = []
    for row in all_rows[1:]:  # skip header row
        while len(row) < 4:
            row.append("")
        users.append({
            "Email":    row[0].strip(),
            "Password": row[1].strip(),
            "Name":     row[2].strip(),
            "Active":   row[3].strip(),
        })
    return users


def authenticate(email: str, password: str):
    users = load_users()
    email_lower = email.strip().lower()
    pw_hash = hash_password(password)

    for user in users:
        if user["Email"].lower() == email_lower:
            if user["Active"].upper() != "TRUE":
                return None  # account suspended
            if user["Password"] == pw_hash:
                return user
    return None


# ── Data helpers ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_scenarios():
    gc = get_google_client()
    rows = gc.open("AI Tutor Scenarios").sheet1.get_all_records()
    return rows


def get_tasks_for_subject(subject):
    rows = load_scenarios()
    return [r for r in rows if str(r.get("Subject", "")).strip().lower() == subject.lower()]


DEFAULT_GRADING_PROMPT = (
    "You are an academic tutor at the Institute of Accounting Science.\n\n"
    "Scenario:\n{scenario}\n\n"
    "Question:\n{question}\n\n"
    "Student Answer:\n{answer}\n\n"
    "Grade the student's answer out of 100 based on understanding, analysis, "
    "evidence and recommendations.\n\n"
    "Return ONLY valid JSON with no extra text:\n"
    '{{"score": 0, "strengths": [], "weaknesses": [], "feedback": ""}}'
)


def grade_answer(scenario_text, question_text, student_answer, custom_prompt=""):
    if custom_prompt and custom_prompt.strip():
        try:
            prompt = custom_prompt.format(
                scenario=scenario_text,
                question=question_text,
                answer=student_answer
            )
        except KeyError:
            prompt = (
                custom_prompt.strip()
                + "\n\nScenario:\n" + scenario_text
                + "\n\nQuestion:\n" + question_text
                + "\n\nStudent Answer:\n" + student_answer
            )
        prompt += (
            '\n\nReturn ONLY valid JSON with no extra text:\n'
            '{"score": 0, "strengths": [], "weaknesses": [], "feedback": ""}'
        )
    else:
        prompt = DEFAULT_GRADING_PROMPT.format(
            scenario=scenario_text,
            question=question_text,
            answer=student_answer
        )
    response = client.responses.create(model="gpt-5", input=prompt)
    return json.loads(response.output_text)


def log_submission(student_id, subject, scenario_id, attempt, score,
                   response_text, strengths, weaknesses, feedback, email=""):
    gc = get_google_client()
    sheet = gc.open("AI Tutor Results").sheet1
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        student_id,
        email,
        subject,
        scenario_id,
        attempt,
        score,
        response_text,
        strengths,
        weaknesses,
        feedback
    ])


# ── Session state defaults ─────────────────────────────────────────────────────

for key, default in {
    "screen":        "login",
    "subject":       None,
    "task":          None,
    "result":        None,
    "user":          None,
    "login_error":   "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Navigation helpers ─────────────────────────────────────────────────────────

def go_home():
    st.session_state.screen = "home"
    st.session_state.subject = None
    st.session_state.task = None
    st.session_state.result = None


def go_tasks(subject):
    st.session_state.subject = subject
    st.session_state.screen = "tasks"
    st.session_state.task = None
    st.session_state.result = None


def go_answer(task):
    st.session_state.task = task
    st.session_state.screen = "answer"
    st.session_state.result = None


def sign_out():
    for key in ["screen", "subject", "task", "result", "user", "login_error"]:
        del st.session_state[key]
    st.rerun()


# ── Sign-out button (shown on every post-login screen) ────────────────────────

def render_signout():
    col_space, col_btn = st.columns([6, 1])
    with col_btn:
        st.markdown('<div class="signout-btn">', unsafe_allow_html=True)
        if st.button("Sign out", key="signout"):
            sign_out()
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 0 — Login
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.screen == "login":

    st.markdown('<div class="login-title">IAS AI Tutor</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Sign in with your institutional Google account and access password</div>',
                unsafe_allow_html=True)

    _, col, _ = st.columns([1, 3, 1])
    with col:
        st.markdown('<div class="field-label">Google account email</div>', unsafe_allow_html=True)
        email_input = st.text_input("Email", placeholder="yourname@gmail.com",
                                    label_visibility="collapsed")

        st.markdown('<div class="field-label" style="margin-top:14px;">Access password</div>',
                    unsafe_allow_html=True)
        password_input = st.text_input("Password", type="password",
                                       placeholder="Enter your access password",
                                       label_visibility="collapsed")

        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

        st.markdown('<div class="login-btn">', unsafe_allow_html=True)
        login_btn = st.button("Sign In", key="login_submit", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.login_error:
            st.error(st.session_state.login_error)

    if login_btn:
        if not email_input.strip():
            st.session_state.login_error = "⚠️ Please enter your email address."
            st.rerun()
        elif not password_input.strip():
            st.session_state.login_error = "⚠️ Please enter your access password."
            st.rerun()
        else:
            with st.spinner("Verifying credentials..."):
                user = authenticate(email_input, password_input)
            if user:
                st.session_state.user          = user
                st.session_state.login_error   = ""
                st.session_state.screen        = "home"
                st.rerun()
            else:
                st.session_state.login_error = (
                    "❌ Email or password not recognised. "
                    "Check your details or contact your lecturer."
                )
                st.rerun()

    st.markdown('<div class="ias-footer">INSTITUTE OF ACCOUNTING SCIENCE · AI TUTOR · CONFIDENTIAL</div>',
                unsafe_allow_html=True)

    st.stop()


# ── Guard: redirect to login if session lost ──────────────────────────────────

if not st.session_state.get("user"):
    st.session_state.screen = "login"
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — Home
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.screen == "home":

    render_signout()

    user = st.session_state.user
    display_name = user.get("Name", user.get("Email", "Student"))
    st.markdown(f'<div class="home-title">IAS AI Tutor</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="user-badge">Signed in as <span>{display_name}</span></div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        if st.button("Manfin", key="btn_manfin", use_container_width=True):
            go_tasks("Manfin")
            st.rerun()
        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
        if st.button("Tax", key="btn_tax", use_container_width=True):
            go_tasks("Tax")
            st.rerun()

    with col2:
        if st.button("Audit", key="btn_audit", use_container_width=True):
            go_tasks("Audit")
            st.rerun()
        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
        if st.button("Finacc", key="btn_finacc", use_container_width=True):
            go_tasks("Finacc")
            st.rerun()

    st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="integrated-btn">', unsafe_allow_html=True)
    if st.button("Integrated", key="btn_integrated", use_container_width=True):
        go_tasks("Integrated")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="ias-footer">INSTITUTE OF ACCOUNTING SCIENCE · AI TUTOR · CONFIDENTIAL</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — Task list
# ══════════════════════════════════════════════════════════════════════════════

elif st.session_state.screen == "tasks":

    render_signout()
    subject = st.session_state.subject

    st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
    if st.button("← Back", key="back_home"):
        go_home()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="screen-title">{subject} — Select your task</div>',
                unsafe_allow_html=True)

    with st.spinner("Loading tasks..."):
        tasks = get_tasks_for_subject(subject)

    if not tasks:
        st.warning(f"No tasks found for {subject} yet. Check back soon.")
    else:
        for i, task in enumerate(tasks):
            title = task.get("Title", f"Task {i+1}")
            scenario_preview = str(task.get("Scenario", ""))[:120] + "…"
            st.markdown('<div class="task-list-btn">', unsafe_allow_html=True)
            if st.button(f"{title}\n\n{scenario_preview}", key=f"task_{i}",
                         use_container_width=True):
                go_answer(task)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="more-tasks-note">More tasks will be available as time continues</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="ias-footer">INSTITUTE OF ACCOUNTING SCIENCE · AI TUTOR · CONFIDENTIAL</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — Answer
# ══════════════════════════════════════════════════════════════════════════════

elif st.session_state.screen == "answer":

    render_signout()
    task = st.session_state.task

    st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
    if st.button("← Back to tasks", key="back_tasks"):
        st.session_state.screen = "tasks"
        st.session_state.result = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    title         = task.get("Title", "Task")
    scenario      = task.get("Scenario", "")
    question      = task.get("Question", "")
    custom_prompt = task.get("Prompt", "")

    st.markdown(f'<div class="answer-header">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="answer-body"><strong>Scenario</strong><br>{scenario}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="answer-body"><strong>Question</strong><br>{question}</div>',
                unsafe_allow_html=True)

    st.markdown('<div class="field-label">Student Number</div>', unsafe_allow_html=True)
    student_id = st.text_input("Student Number", placeholder="e.g. 20222526",
                               label_visibility="collapsed")

    st.markdown('<div class="field-label" style="margin-top:14px;">Your answer</div>',
                unsafe_allow_html=True)
    answer = st.text_area("Your answer",
                          placeholder="Write your answer here...",
                          height=200,
                          label_visibility="collapsed")

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    st.markdown('<div class="submit-btn">', unsafe_allow_html=True)
    submit = st.button("SUBMIT")
    st.markdown('</div>', unsafe_allow_html=True)

    if submit:
        if not student_id.strip():
            st.warning("⚠️ Student Number is required before submitting.")
        elif not answer.strip():
            st.warning("⚠️ Please write your answer before submitting.")
        else:
            with st.spinner("Analysing your answer..."):
                result = grade_answer(scenario, question, answer, custom_prompt)

            logged_email = st.session_state.user.get("Email", "")

            st.session_state.result = {
                "score":      result["score"],
                "strengths":  ", ".join(result["strengths"]),
                "weaknesses": ", ".join(result["weaknesses"]),
                "feedback":   result["feedback"],
                "student_id": student_id,
                "answer":     answer,
            }

            try:
                log_submission(
                    student_id    = student_id,
                    subject       = st.session_state.subject,
                    scenario_id   = task.get("ScenarioID", ""),
                    attempt       = 1,
                    score         = result["score"],
                    response_text = answer,
                    strengths     = ", ".join(result["strengths"]),
                    weaknesses    = ", ".join(result["weaknesses"]),
                    feedback      = result["feedback"],
                    email         = logged_email,
                )
            except Exception:
                pass

            st.session_state.screen = "result"
            st.rerun()

    st.markdown('<div class="ias-footer">INSTITUTE OF ACCOUNTING SCIENCE · AI TUTOR · CONFIDENTIAL</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — Result
# ══════════════════════════════════════════════════════════════════════════════

elif st.session_state.screen == "result":

    render_signout()
    r = st.session_state.result
    score = r["score"]

    if score >= 75:
        grade_class, grade_label = "grade-pass",       "✅ Pass"
    elif score >= 50:
        grade_class, grade_label = "grade-borderline", "⚠️ Borderline"
    else:
        grade_class, grade_label = "grade-fail",       "❌ Needs Work"

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
            <p>{r["strengths"]}</p>
        </div>
        <div class="result-card card-weaknesses">
            <h4>⚠️ Areas to Improve</h4>
            <p>{r["weaknesses"]}</p>
        </div>
        <div class="result-card card-feedback">
            <h4>💡 Tutor Feedback</h4>
            <p>{r["feedback"]}</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="result-nav">', unsafe_allow_html=True)
        if st.button("Try another task", use_container_width=True):
            st.session_state.screen = "tasks"
            st.session_state.result = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="result-nav">', unsafe_allow_html=True)
        if st.button("Back to subjects", use_container_width=True):
            go_home()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="ias-footer">INSTITUTE OF ACCOUNTING SCIENCE · AI TUTOR · CONFIDENTIAL</div>',
                unsafe_allow_html=True)