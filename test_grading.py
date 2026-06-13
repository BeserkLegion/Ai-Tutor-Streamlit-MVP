from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

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

    return json.loads(response.output_text)


result = grade_answer(
    """
    AI can improve accounting by automating
    repetitive tasks and reducing errors.
    """
)

print(result)