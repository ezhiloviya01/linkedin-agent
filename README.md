# LinkedIn Marketing Agent

## Project Overview

The LinkedIn Marketing Agent is a Flask-based application that helps users generate, review, approve, schedule, and publish LinkedIn posts.

It uses Google Gemini for AI-generated content and LinkedIn OAuth 2.0 for account authentication.

## Features

- LinkedIn OAuth login and authentication.
- Client onboarding and content preferences.
- AI-generated LinkedIn post drafts using Gemini.
- Backend content guardrail checks.
- Post approval and rejection workflow.
- Scheduled LinkedIn publishing.
- Neon PostgreSQL database for storing application data.
- Encrypted LinkedIn access-token storage.
- Token expiry checks and error handling.

## Technologies Used

- Python 3.12
- Flask
- Google Gemini API
- LinkedIn API
- Neon PostgreSQL
- psycopg2
- APScheduler
- Cryptography (Fernet)
- HTML and CSS

## Project Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ezhiloviya01/linkedin-agent.git
cd linkedin-agent
```

### 2. Create a Virtual Environment

```bash
py -3.12 -m venv venv
```

Activate the virtual environment on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root directory.

Add the following variables:

```env
GEMINI_API_KEY=your_gemini_api_key
FLASK_SECRET_KEY=your_flask_secret_key
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=your_linkedin_redirect_uri
TOKEN_ENCRYPTION_KEY=your_fernet_encryption_key
DATABASE_URL=your_neon_postgresql_connection_string
```

Replace the placeholder values with your actual credentials.

**Important:** Never commit your `.env` file or expose API keys, OAuth secrets, database credentials, or encryption keys.

## Run the Application Locally

Start the Flask application:

```bash
py -3.12 oauth_server.py
```

Open the local URL displayed in the terminal in your browser.

## Scheduled Publishing

The project uses APScheduler to check for approved posts that are due for publishing.

The scheduler is implemented in `background_scheduler.py`.

Run it separately when scheduled publishing is intended:

```bash
py -3.12 background_scheduler.py
```

Keep the scheduler stopped when you do not want automatic publishing.

For production, the background scheduler should run as a separate worker process or service, not as part of the Flask web server process.

## Deployment

The application is deployed on Render.

The deployment configuration is defined in `render.yaml`.

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn --timeout 180 oauth_server:app`

Configure the required environment variables in the Render dashboard, including `DATABASE_URL`.

Ensure that the LinkedIn OAuth redirect URI matches the deployed callback URL.

## Database

The application uses **Neon PostgreSQL** as its database.

The database stores:

- Scheduled posts and publishing statuses.
- Posting schedules and time zones.
- LinkedIn credentials and token expiry information.
- Client configurations.

The application connects to Neon PostgreSQL using the `DATABASE_URL` environment variable and the `psycopg2` library.

Database initialization and table creation are handled by the `init_db()` function in `scheduler.py`.

The `db_connection()` context manager handles database commits, rollbacks, and connection closure.

## Security

- LinkedIn access tokens are encrypted before database storage.
- Token expiry is checked before publishing.
- Flask session data stores the LinkedIn member ID rather than the access token.
- Environment variables are used to manage sensitive credentials.
- Publishing failures are recorded with error details.

## Project Workflow

1. User logs in through LinkedIn OAuth.
2. User completes onboarding and content preferences.
3. User generates a LinkedIn post draft.
4. Backend guardrails check the generated content.
5. User reviews and approves or rejects the draft.
6. Approved posts can be scheduled.
7. The background scheduler checks due posts and attempts publishing.
8. Publishing results and failures are recorded in Neon PostgreSQL.