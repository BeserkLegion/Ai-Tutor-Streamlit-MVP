import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json",
    scope
)

client = gspread.authorize(creds)

sheet = client.open("AI Tutor Results").sheet1

sheet.append_row([
    "TEST",
    "Student001",
    "Scenario1",
    1,
    85,
    "This is a test answer",
    "Good structure",
    "Needs more detail",
    "Overall good"
])

print("Success!")