import os
import json
import requests
import secrets
from flask import Flask, redirect, request, render_template
from generate_post import generate_post
from check_post import check_post
from approval import set_pending_post, get_pending_post, approve_post, reject_post
from publish import publish_post
from dotenv import load_dotenv, set_key
from urllib.parse import urlencode
load_dotenv()
oauth_states = set()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-dev-secret-key")
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

SCOPE = "openid profile w_member_social"



@app.route("/", methods=["GET", "POST"])

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        client_config = {
            "client_name": request.form.get("client_name", "").strip(),
            "business_description": request.form.get("business_description", "").strip(),
            "industry": request.form.get("industry", ""),
            "company_size": request.form.get("company_size", ""),
            "products_services": request.form.get("products_services", "").strip(),

            # Questionnaire preferences
            "content_goals": request.form.getlist("content_goals"),
            "post_types": request.form.getlist("post_types"),
            "posting_frequency": request.form.get("posting_frequency", ""),
            "post_styles": request.form.getlist("post_styles"),
            "target_audience": request.form.getlist("target_audience"),
            "post_formats": request.form.getlist("post_formats"),

            # Backend-controlled guardrails
            "topics_to_avoid": [
                "False information",
                "Unverified claims",
                "Confidential information",
                "Private information",
                "Offensive content",
                "Unrelated topics",
                "Attacking competitors"
            ],
            "content_rules": [
                "Do not make unsupported claims",
                "Do not share confidential or private information",
                "Keep content professional and helpful",
                "Never publish without human approval"
            ]
        }

        with open("client_config.json", "w", encoding="utf-8") as file:
            json.dump(client_config, file, indent=4)

        return redirect("/login")

    return render_template("onboarding.html")




@app.route("/login")
def login():
    state = secrets.token_urlsafe(16)
    oauth_states.add(state)
    print("SAVED STATE:", state)
    authorization_url = AUTH_URL + "?" + urlencode({
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "state": state
})

    return redirect(authorization_url)


@app.route("/callback")
def callback():
    returned_state = request.args.get("state")

    if returned_state not in oauth_states:
        return "Invalid OAuth state"

    oauth_states.remove(returned_state)

    print("RETURNED STATE:", returned_state)
    
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

    userinfo_response = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )

    userinfo = userinfo_response.json()
    member_id = userinfo.get("sub")

    set_key(".env", "LINKEDIN_ACCESS_TOKEN", access_token)
    set_key(".env", "LINKEDIN_MEMBER_ID", member_id)

    return redirect("/generate-post")

    return f"OAuth failed: {token_data}"


@app.route("/generate-post", methods=["GET", "POST"])
def generate_post_page():
    # Load the saved company profile and questionnaire preferences
    with open("client_config.json", "r", encoding="utf-8") as file:
        client_config = json.load(file)

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()

        post = generate_post(topic)

        return render_template(
            "generate_post.html",
            config=client_config,
            topic=topic,
            post=post
        )

    return render_template(
        "generate_post.html",
        config=client_config,
        topic="",
        post=None
    )


@app.route("/check-post", methods=["GET", "POST"])
def check_post_page():
    if request.method == "POST":
        post = request.form.get("post", "")
        result = check_post(post)

        if result.strip().startswith("PASS"):
            set_pending_post(post, result)
            return redirect("/approval")

        return render_template(
            "check_post.html",
            post=post,
            result=result
        )

    return render_template("check_post.html")

@app.route("/approval")
def approval_page():
    post, result = get_pending_post()

    return render_template(
        "approval.html",
        post=post,
        result=result
    )


@app.route("/approve", methods=["POST"])
def approve():
    post = approve_post()

    if not post:
        return "<h1>No post available for publishing.</h1>"

    result = publish_post(post)

    return f"""
    <h1>Publishing Result</h1>
    <p>{result}</p>
    <pre>{post}</pre>
    """


@app.route("/reject", methods=["POST"])
def reject():
    reject_post()

    return """
    <h1>Post Rejected</h1>
    <p>The post has been rejected.</p>
    """


if __name__ == "__main__":
    app.run(port=8000, debug=True)
