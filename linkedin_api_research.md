# LinkedIn API Research — Day 1

## 1. OAuth / Authentication

LinkedIn uses OAuth 2.0 for applications that need to access LinkedIn
on behalf of a user.

The Authorization Code Flow (3-legged OAuth) involves:

1. Configure the LinkedIn application.
2. Send the user to LinkedIn's authorization page.
3. User authorizes the application.
4. LinkedIn returns an authorization code.
5. Exchange the authorization code for an access token.
6. Use the access token to make authenticated API requests.

The access token is then used when making requests to LinkedIn APIs.

---

## 2. LinkedIn Posting Permissions

LinkedIn provides permissions/scopes that control what an application
can do.

For member posting, LinkedIn documents the `w_member_social`
permission.

For organization/page posting, LinkedIn documents the
`w_organization_social` permission.

Organization posting also requires the appropriate organization role.

---

## 3. Organization Posts API

LinkedIn provides a Posts API for creating and managing posts.

Endpoint researched:

POST https://api.linkedin.com/rest/posts

Authenticated requests use an OAuth access token.

The request includes LinkedIn-specific headers and identifies the
organization as the author of the post.

---

## 4. Important Finding

Before building the full publishing integration, we need to confirm
which LinkedIn API products and permissions are available to our
application.

We also need to confirm whether each client needs a separate LinkedIn
Developer application or whether one BridgeE-owned application can be
used for multiple client instances.

---
## LinkedIn API/ToS Reality

### API Access and Permission Limitations

LinkedIn API access depends on the API products and permissions available to the Developer App.

For member posting:
- `w_member_social` is required.

For organization/company page posting:
- `w_organization_social` is required.
- The authenticated user must have the required organization role.

The required API products and permissions must be approved and confirmed before implementing production publishing.

### Per-Client vs. Shared Developer App

**Status: PENDING CONFIRMATION**

The LinkedIn documentation reviewed so far does not clearly confirm whether multiple independent client instances can use one BridgeE-owned Developer App, or whether each client instance must register its own LinkedIn Developer App.

Therefore, this decision remains pending confirmation with LinkedIn.

Until this is confirmed, development and testing should use one sandboxed LinkedIn account, as specified in the project scope.


## Initial Agent Workflow

Client configuration
        ↓
LinkedIn OAuth connection
        ↓
Generate LinkedIn post
        ↓
Check post against guardrails
        ↓
Human approval
        ↓
Publish through LinkedIn API


## Competitor Research

### 1. Buffer
- Social media management platform supporting LinkedIn and other platforms.
- Provides an AI Assistant for brainstorming ideas, rewriting content, and creating platform-specific posts.
- Supports managing, editing, and approving posts as a team.
- Provides scheduling and publishing features.
- Also provides analytics/insights and comment management.

### 2. Hootsuite
- Social media management platform for creating, managing, and publishing social content.
- Provides AI-supported insights and content workflows.
- Allows users to create content, manage social accounts, and engage with customers from one platform.
- Supports monitoring trends, conversations, and competitors.
- Provides analytics and reporting features.

### Key observations for our LinkedIn AI Agent
- AI can help generate and improve social media content.
- Social media tools commonly include scheduling/publishing.
- Team workflows can include editing and approval before publishing.
- Our tool will focus specifically on LinkedIn and use a human approval step before publishing.

## Content-Generation Approach

The LinkedIn AI Agent will use the Claude API to generate LinkedIn post drafts.

### Proposed Flow

1. Load the client's configuration:
   - Business information
   - Products/services
   - Target audience
   - Brand voice
   - Topics to post about
   - Topics to avoid
   - Content rules

2. The user provides a topic or content idea.

3. The client configuration and topic are sent to Claude.

4. Claude generates a LinkedIn post draft that follows the client's
   brand voice and content rules.

5. The generated post is sent to a separate guardrail check.

6. The post is then sent for human review and approval.

7. Only approved content can move to publishing.

### Key Approach

- Use Claude API for content generation.
- Generate content based on each client's configuration.
- Keep the writing aligned with the client's brand voice.
- Avoid topics and content restricted by the client's rules.
- Keep generation and guardrail checking as separate steps.
- Never publish AI-generated content without human approval.

## Approval-Workflow Patterns

The LinkedIn AI Agent will use a human-in-the-loop approval workflow.

### Proposed Workflow

1. Claude generates a LinkedIn post draft.

2. The draft is checked against the content guardrails.

3. The draft is placed in an approval queue.

4. The human reviewer can:
   - Review the post
   - Edit the post
   - Approve the post
   - Reject the post

5. Only approved posts can move to the publishing stage.

6. The system records the publishing activity.

### Key Approach

- AI should not publish content automatically.
- Human approval is required before publishing.
- The reviewer should be able to edit the AI-generated draft.
- Rejected content should not be published.
- Approved content can be passed to the LinkedIn publishing layer.
- The system should keep a record of what was approved and published.

### Competitor Observation

Buffer provides team-oriented workflows where social media posts can be
managed, edited, and approved before publishing.

This supports using an approval queue as part of the LinkedIn AI Agent.

### Proposed Agent Workflow

Generate
   ↓
Guardrail Check
   ↓
Approval Queue
   ↓
Human Edit / Approve / Reject
   ↓
Approved
   ↓
Publish
   ↓
Activity Log

