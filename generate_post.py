
import json
import os
import time
import re

from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def generate_post(topic):
    # Load the latest client configuration
    with open("client_config.json", "r", encoding="utf-8") as file:
        client_config = json.load(file)

    prompt = f"""
You are a LinkedIn content writer for the following company.

COMPANY PROFILE
Company name:
{client_config.get("client_name", "")}

Business description:
{client_config.get("business_description", "")}

Industry:
{client_config.get("industry", "")}

Company size:
{client_config.get("company_size", "")}

Products and services:
{json.dumps(client_config.get("products_services", ""))}

USER PERSONA
Professional role:
{client_config.get("user_role", "")}

Areas of expertise:
{client_config.get("user_expertise", "")}

Personal branding goal:
{client_config.get("personal_branding_goal", "")}

Preferred writing perspective:
{client_config.get("user_perspective", "")}


CONTENT PREFERENCES
Main content goals:
{json.dumps(client_config.get("content_goals", []))}

Preferred post types:
{json.dumps(client_config.get("post_types", []))}

Posting frequency:
{client_config.get("posting_frequency", "")}

Preferred writing styles:
{json.dumps(client_config.get("post_styles", []))}

Target audiences:
{json.dumps(client_config.get("target_audience", []))}

Preferred post formats:
{json.dumps(client_config.get("post_formats", []))}

BACKEND-CONTROLLED GUARDRAILS
Content rules:
{json.dumps(client_config.get("content_rules", []), indent=2)}

Topics to avoid:
{json.dumps(client_config.get("topics_to_avoid", []), indent=2)}


REQUEST
Create one LinkedIn post draft about:
{topic}

EXPERT WRITING EXAMPLES
Use these examples to understand the expected quality, depth, and style.
Learn from the writing approach, but do not copy their wording or force every
post to follow the same structure.

Example 1 — Practical marketing insight:
"Getting attention is only the first step in marketing. The real challenge is
helping people understand why a product matters to them.

A useful starting point is to focus on the problem a customer is trying to
solve. When the message connects the product to that problem, the value becomes
clearer.

Good marketing doesn't just explain what a product does. It explains why
someone should care."

Example 2 — Learning and professional growth:
"Learning a new tool is easy compared with understanding when to use it.

A tool might help automate a task, but the bigger question is whether that task
actually needs automation. Sometimes, improving the process first creates more
value than adding another tool.

The goal isn't to use more technology. It's to solve the right problem."

INSTRUCTIONS
- Write like an experienced marketing professional sharing genuine insights on LinkedIn, not like an AI generating generic content.
- Demonstrate expertise through clear reasoning, industry understanding, practical examples, and useful takeaways.
- When discussing a practical application, explain at least one meaningful implementation consideration, decision, trade-off, or way to measure success when relevant. Avoid merely listing tools or technical terms.
- Whenever relevant, explain a practical workflow, decision, trade-off, or real-world application instead of relying on broad claims or general advice.
- Go beyond describing a topic. Explain why it matters, what can be learned from it, or how it can be applied in practice.
- Start with a strong, natural hook that makes the reader want to continue.
- Use conversational, professional language that sounds authentic and human.
- Share specific, useful insights relevant to the company's industry, products, services, and target audience.
- Explain ideas clearly using natural sentence structures and varied sentence lengths.
- Avoid clichés, exaggerated claims, robotic transitions, repetitive phrases, and generic motivational statements.
- Avoid formulaic openings such as "In today's fast-paced digital world" and "In an ever-evolving landscape."
- Do not force numbered lists, excessive bullet points, emojis, or hashtags. Use them only when they genuinely improve the post.
- Avoid making every post follow the same structure.
- Use only one blank line between paragraphs.
- Do not add multiple consecutive blank lines or unnecessary spacing.
- Keep the post concise, engaging, and suitable for LinkedIn.
- End naturally with a meaningful takeaway or relevant question when appropriate.
- Align the post with the user's professional role, expertise, personal branding goal, and preferred writing perspective.
- Follow the company's content goals, post types, writing styles, target audience, and post formats.
- Respect all backend-controlled guardrails and topics to avoid.
- Never invent statistics, facts, customer stories, personal experiences, or unsupported claims.
- Write in the first person only when the user's actual experience is provided in the client configuration or request. Clearly distinguish established facts from suggestions or possibilities.
- Do not imply that the user personally performed, experienced, tested, or discovered something unless that experience is explicitly provided. When no personal experience is available, write from an informative professional perspective instead.
- Do not reveal confidential or private information.
- Do not publish the post. Generate a draft for human review.
- Return only the LinkedIn post draft, without explanations.
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )


            post = response.text or ""

            # Normalize paragraph spacing
            post = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", post)

            return post.strip() or (
                "Gemini returned an empty response. Please try again."
            )


        except ServerError as exc:
            print(f"Gemini server error on attempt {attempt + 1}: {exc}")

            if attempt == 2:
                print("Gemini remained unavailable after 3 attempts.")
                return (
                    "Gemini is temporarily unavailable. Please wait a "
                    "little while and try generating your post again."
                )

            time.sleep(2 * (attempt + 1))

        except Exception as exc:
            print("Gemini error:", repr(exc))
            return (
                "Post generation failed. Please check the VS Code terminal "
                "for the error details."
            )


if __name__ == "__main__":
    topic = input("Enter a topic for the LinkedIn post: ")
    post = generate_post(topic)

    print("\n--- GENERATED LINKEDIN POST ---\n")
    print(post)
