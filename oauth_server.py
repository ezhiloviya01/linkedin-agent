
import os
import json
import secrets
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import (
    Flask,
    redirect,
    request,
    render_template,
    session
)
from dotenv import load_dotenv
from urllib.parse import urlencode

from generate_post import generate_post
from check_post import check_post
from approval import (
    set_pending_post,
    get_pending_post,
    approve_post,
    reject_post
)
from publish import publish_post

from scheduler import (
    init_db,
    save_schedule,
    add_scheduled_post,
    approve_scheduled_post,
    reject_scheduled_post,
    get_pending_scheduled_posts,
    get_schedule
)


load_dotenv()
init_db()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is missing from the environment.")

app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

SCOPE = "openid profile w_member_social"

# OAuth state values for the current application process.
oauth_states = set()


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":

        # Read the user's selected posting days and times.
        client_name = request.form.get("client_name", "").strip()
        schedule_days = request.form.getlist("schedule_days")

        days_and_times = {}

        valid_days = {
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        }

        for day in schedule_days:
            if day not in valid_days:
                continue

            selected_time = request.form.get(f"time_{day}", "")

            # Validate the time format.
            if selected_time:
                try:
                    from datetime import datetime
                    datetime.strptime(selected_time, "%H:%M")
                    days_and_times[day] = selected_time
                except ValueError:
                    return f"Invalid time selected for {day}.", 400

        if not client_name:
            return "Please enter a company name.", 400

        if not days_and_times:
            return "Please select at least one posting day and time.", 400

        # Save the recurring schedule in SQLite.
        save_schedule(
            user_id=client_name,
            days_and_times=days_and_times,
            timezone="Asia/Kolkata"
        )

        # Save the existing company and content preferences.
        client_config = {

            "client_name": client_name,
            "user_role": request.form.get("user_role", "").strip(),
            "user_expertise": request.form.get("user_expertise", "").strip(),
            "personal_branding_goal": request.form.get("personal_branding_goal", "").strip(),
            "user_perspective": request.form.get("user_perspective", "").strip(),
            "business_description": request.form.get(
            "business_description", ""
            ).strip(),
            "industry": request.form.get("industry", ""),
            "company_size": request.form.get("company_size", ""),
            "products_services": request.form.get(
                "products_services", ""
            ).strip(),
            "content_goals": request.form.getlist("content_goals"),
            "post_types": request.form.getlist("post_types"),
            "posting_frequency": request.form.get(
                "posting_frequency", ""
            ),
            "post_styles": request.form.getlist("post_styles"),
            "target_audience": request.form.getlist(
                "target_audience"
            ),
            "post_formats": request.form.getlist("post_formats"),
            "schedule_days": days_and_times,
            "timezone": "Asia/Kolkata",

            # Backend-controlled guardrails.
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
    if not CLIENT_ID or not REDIRECT_URI:
        return "LinkedIn OAuth configuration is missing.", 500

    state = secrets.token_urlsafe(32)
    oauth_states.add(state)

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

    if not returned_state or returned_state not in oauth_states:
        return "Invalid OAuth state. Please try logging in again.", 400

    oauth_states.remove(returned_state)

    if request.args.get("error"):
        return (
            "LinkedIn authorization was cancelled or denied: "
            + request.args.get("error")
        ), 400

    code = request.args.get("code")

    if not code:
        return "LinkedIn authorization code was not received.", 400

    if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
        return "LinkedIn OAuth configuration is incomplete.", 500

    try:
        token_response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            },
            timeout=30
        )

        if not token_response.ok:
            app.logger.error(
                "LinkedIn token exchange failed: %s",
                token_response.text
            )
            return (
                "LinkedIn token exchange failed. "
                "Check the application logs."
            ), 400

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            return "LinkedIn did not return an access token.", 400

        userinfo_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=30
        )

        if not userinfo_response.ok:
            app.logger.error(
                "LinkedIn user information request failed: %s",
                userinfo_response.text
            )
            return (
                "Could not retrieve your LinkedIn account information."
            ), 400

        userinfo = userinfo_response.json()
        member_id = userinfo.get("sub")

        if not member_id:
            return "LinkedIn member ID was not returned.", 400

        session["LINKEDIN_ACCESS_TOKEN"] = access_token
        session["LINKEDIN_MEMBER_ID"] = member_id

        return redirect("/generate-post")

    except (requests.RequestException, ValueError):
        app.logger.exception("LinkedIn OAuth request failed")
        return "LinkedIn connection failed. Please try again.", 500


@app.route("/generate-post", methods=["GET", "POST"])
def generate_post_page():
    try:
        with open("client_config.json", "r", encoding="utf-8") as file:
            client_config = json.load(file)
    except (OSError, json.JSONDecodeError):
        return redirect("/")

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()

        if not topic:
            return render_template(
                "generate_post.html",
                config=client_config,
                topic=topic,
                post="Please enter a topic before generating a post."
            )

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
        post = request.form.get("post", "").strip()

        if not post:
            return render_template(
                "check_post.html",
                post=post,
                result="FAIL: The post is empty."
            )

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

    if not post:
        return (
            "<h1>No pending post found.</h1>"
            "<p>Please generate a post and pass the guardrail check again.</p>"
        ), 400

    return render_template(
        "approval.html",
        post=post,
        result=result
    )



@app.route("/approve", methods=["POST"])
def approve():
    pending_post, result = get_pending_post()

    if not pending_post:
        return "No pending post available. Generate and check a post again.", 400

    access_token = session.get("LINKEDIN_ACCESS_TOKEN")
    member_id = session.get("LINKEDIN_MEMBER_ID")

    if not access_token or not member_id:
        return "Please reconnect your LinkedIn account.", 401

    try:
        with open("client_config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
    except (OSError, json.JSONDecodeError):
        return "Could not read client configuration.", 500

    client_name = config.get("client_name", "").strip()
    schedule = get_schedule(client_name) if client_name else None

    if not schedule or not schedule.get("days_and_times"):
        return "No posting schedule found. Configure your schedule first.", 400

    timezone = ZoneInfo(schedule.get("timezone", "Asia/Kolkata"))
    now = datetime.now(timezone)
    weekdays = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    ]
    candidates = []

    for day, time_str in schedule["days_and_times"].items():
        try:
            hour, minute = map(int, time_str.split(":"))
            days_ahead = (weekdays.index(day) - now.weekday()) % 7

            candidate = (now + timedelta(days=days_ahead)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

            if candidate <= now:
                candidate += timedelta(days=7)

            candidates.append(candidate)
        except (ValueError, TypeError):
            continue

    if not candidates:
        return "No valid posting times found.", 400

    scheduled_time = min(candidates)
    scheduled_at = scheduled_time.astimezone(
        ZoneInfo("UTC")
    ).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    post = approve_post()

    if not post:
        return "Could not retrieve the approved post.", 400

    post_id = add_scheduled_post(
        post_text=post,
        scheduled_day=scheduled_time.strftime("%A"),
        scheduled_time=scheduled_time.strftime("%H:%M"),
        timezone=str(timezone),
        user_id=client_name,
        scheduled_at=scheduled_at,
        access_token=access_token,
        member_id=member_id
    )

    if not approve_scheduled_post(post_id):
        return "Could not approve the scheduled post.", 500

    return render_template(
        "approval.html",
        post=post,
        result=(
            "Post approved and scheduled for "
            + scheduled_time.strftime("%A, %d %B at %I:%M %p")
            + " (" + str(timezone) + "). It has not been published yet."
        )
    )



@app.route("/reject", methods=["POST"])
def reject():
    reject_post()

    return """
    <h1>Post Rejected</h1>
    <p>The post has been rejected and will not be published.</p>
    """



@app.route("/scheduled-approvals/<int:post_id>/approve", methods=["POST"])
def approve_scheduled(post_id):
    success = approve_scheduled_post(post_id)

    if not success:
        return (
            "This scheduled post was not found or is no longer awaiting approval.",
            404
        )

    return redirect("/scheduled-approvals")



@app.route("/scheduled-approvals")
def scheduled_approvals():
    posts = get_pending_scheduled_posts()
    return render_template(
        "scheduled_approvals.html",
        posts=posts
    )


@app.route("/scheduled-approvals/<int:post_id>/reject", methods=["POST"])
def reject_scheduled(post_id):
    success = reject_scheduled_post(post_id)

    if not success:
        return (
            "This scheduled post was not found or is no longer awaiting approval.",
            404
        )

    return redirect("/scheduled-approvals")



if __name__ == "__main__":
    app.run(port=8000, debug=True)
