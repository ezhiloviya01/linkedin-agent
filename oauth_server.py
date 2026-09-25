import os
import requests
from flask import Flask, redirect, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

SCOPE = "w_member_social"


@app.route("/")
def home():
    return '<a href="/login">Connect LinkedIn</a>'


@app.route("/login")
def login():
    authorization_url = (
        f"{AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPE}"
    )

    return redirect(authorization_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "Authorization failed."

    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )

    token_data = response.json()        

    if "access_token" in token_data:
        access_token = token_data["access_token"]

        with open(".env", "a", encoding="utf-8") as file:
            file.write(f"\nLINKEDIN_ACCESS_TOKEN={access_token}\n")

        return "LinkedIn OAuth successful! Access token saved."

    return f"OAuth failed: {token_data}"


if __name__ == "__main__":
    app.run(port=8000, debug=True)