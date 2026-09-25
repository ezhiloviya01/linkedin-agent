# LinkedIn Marketing Agent

import json
from dotenv import load_dotenv
load_dotenv()
import os

linkedin_client_id = os.getenv("LINKEDIN_CLIENT_ID")
linkedin_client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
linkedin_redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")
print("LinkedIn Client ID loaded:", bool(linkedin_client_id))
print("LinkedIn Client Secret loaded:", bool(linkedin_client_secret))
print("LinkedIn Redirect URI:", linkedin_redirect_uri)

with open("client_config.json", "r", encoding="utf-8") as file:
    client_config = json.load(file)

print("Client loaded:", client_config["client_name"])

def load_research():
    with open("linkedin_api_research.md", "r", encoding="utf-8") as file:
        return file.read()


research = load_research()

print("=== LinkedIn Marketing Agent ===")
print()
print("LinkedIn API Research: LOADED")
print("Company Guidelines: LOADED")
print()
print("OAuth: Research completed")
print("Posting Permissions: Research completed")
print("Posts API: Research completed")
print()
print("Agent is ready.")
print("----------------------------------------")


def load_guidelines():
    with open("company_guidelines.txt", "r", encoding="utf-8") as file:
        return file.read()


guidelines = load_guidelines()

print("Company guidelines loaded successfully.")

def create_post(topic):
    print("\nCreating LinkedIn post...")
    print(f"Topic: {topic}")
    print("Post will follow the company guidelines.")


def check_post(post):
    print("\nChecking LinkedIn post...")

    blocked_words = [
        "guarantee",
        "best company",
        "100% success"
    ]

    for word in blocked_words:
        if word.lower() in post.lower():
            print("Status: NEEDS CHANGES")
            print(f"Reason: Unsupported claim found: {word}")
            return

    print("Status: APPROVED")
    print("The post follows the basic content rules.")


def create_comment(topic):
    print("\nCreating LinkedIn comment...")
    print(f"Comment topic: {topic}")
    print("Comment should be relevant and professional.")


def check_comment(comment):
    print("\nChecking LinkedIn comment...")

    if len(comment.strip()) < 10:
        print("Status: NEEDS CHANGES")
        print("Reason: Comment is too short.")
    else:
        print("Status: APPROVED")
        print("Comment is suitable for review.")


# Test the agent

# Run the agent

print("\n=== LinkedIn Marketing Agent ===")

topic = input("\nEnter a topic for your LinkedIn post: ")

create_post(topic)

post = input("\nEnter a LinkedIn post to check: ")

check_post(post)

approval = input("\nDo you approve this content? (yes/no): ")

if approval.lower() == "yes":
    print("\nAPPROVED")
    print("Content is ready for publishing.")
else:
    print("\nREJECTED")
    print("Content will not be published.")