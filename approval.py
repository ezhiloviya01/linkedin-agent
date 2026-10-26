
from flask import session
from activity_log import log_activity


def set_pending_post(post, result):
    session["pending_post"] = post
    session["pending_result"] = result


def get_pending_post():
    return session.get("pending_post"), session.get("pending_result")


def approve_post():
    post = session.get("pending_post")
    session.pop("pending_post", None)
    session.pop("pending_result", None)
    return post


def reject_post():
    post = session.get("pending_post")
    session.pop("pending_post", None)
    session.pop("pending_result", None)

    if post:
        log_activity("Reject Post", "REJECTED", post)
