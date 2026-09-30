# Stores the post waiting for human approval
pending_post = None
pending_result = None


def set_pending_post(post, result):
    global pending_post, pending_result

    pending_post = post
    pending_result = result


def get_pending_post():
    return pending_post, pending_result


def approve_post():
    global pending_post, pending_result

    post = pending_post

    pending_post = None
    pending_result = None

    return post


def reject_post():
    global pending_post, pending_result

    pending_post = None
    pending_result = None