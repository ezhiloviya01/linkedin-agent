import os
import json
import requests
from flask import Flask, redirect, request, render_template
from generate_post import generate_post
from check_post import check_post
from approval import set_pending_post, get_pending_post, approve_post, reject_post
from publish import publish_post
from dotenv import load_dotenv, set_key
load_dotenv()

app = Flask(__name__)

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

SCOPE = "openid profile w_member_social"


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        client_config = {
            "client_name": request.form.get("client_name", ""),
            "business_description": request.form.get("business_description", ""),
            "products_services": request.form.get("products_services", ""),
            "target_audience": request.form.get("target_audience", ""),
            "brand_voice": request.form.get("brand_voice", ""),
            "topics_to_post": request.form.get("topics_to_post", ""),
            "topics_to_avoid": request.form.get("topics_to_avoid", ""),
            "content_rules": request.form.get("content_rules", "")
        }

        with open("client_config.json", "w", encoding="utf-8") as file:
            json.dump(client_config, file, indent=4)

        return redirect("/login")

    return render_template("onboarding.html")


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

    userinfo_response = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )

    userinfo = userinfo_response.json()
    member_id = userinfo.get("sub")

    with open(".env", "a", encoding="utf-8") as file:
        file.write(f"\nLINKEDIN_ACCESS_TOKEN={access_token}\n")
        file.write(f"LINKEDIN_MEMBER_ID={member_id}\n")

    return redirect("/generate-post")

    return f"OAuth failed: {token_data}"

@app.route("/generate-post", methods=["GET", "POST"])
def generate_post_page():
    if request.method == "POST":
        topic = request.form.get("topic", "")

        post = generate_post(topic)

        return render_template(
            "generate_post.html",
            topic=topic,
            post=post
        )

    return render_template("generate_post.html")

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
