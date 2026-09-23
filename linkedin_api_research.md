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

## 5. Day 1 Conclusion

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