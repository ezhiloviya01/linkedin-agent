import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import background_scheduler

SUCCESS = "Post published successfully on LinkedIn."


class Recorder:
    """Replaces the database and LinkedIn calls and records what happened."""

    def __init__(self, monkeypatch, due_batches, publish_result=SUCCESS, credentials=True):
        self.batches = list(due_batches)
        self.published_texts = []
        self.marked_published = []
        self.marked_failed = []

        def fake_claim_due_posts():
            return self.batches.pop(0) if self.batches else []

        def fake_get_credentials(user_id):
            if not credentials:
                return None
            return {"access_token": "token", "member_id": "member"}

        def fake_publish(post_text, access_token, member_id):
            self.published_texts.append(post_text)
            return publish_result

        monkeypatch.setattr(background_scheduler, "init_db", lambda: None)
        monkeypatch.setattr(background_scheduler, "claim_due_posts", fake_claim_due_posts)
        monkeypatch.setattr(background_scheduler, "get_linkedin_credentials", fake_get_credentials)
        monkeypatch.setattr(background_scheduler, "publish_post_with_credentials", fake_publish)
        monkeypatch.setattr(background_scheduler, "mark_published", self.marked_published.append)
        monkeypatch.setattr(
            background_scheduler,
            "mark_publish_failed",
            lambda post_id, error: self.marked_failed.append((post_id, error)),
        )


def make_post(post_id=1):
    return {"id": post_id, "user_id": "u1", "member_id": "m1", "post_text": f"Post {post_id}"}


def test_due_post_is_published_once(monkeypatch):
    rec = Recorder(monkeypatch, [[make_post(1)]])
    background_scheduler.check_schedules()
    assert rec.published_texts == ["Post 1"]
    assert rec.marked_published == [1]
    assert rec.marked_failed == []


def test_same_post_not_published_on_second_run(monkeypatch):
    # First run claims the post; second run finds nothing left to claim
    rec = Recorder(monkeypatch, [[make_post(1)], []])
    background_scheduler.check_schedules()
    background_scheduler.check_schedules()
    assert rec.published_texts == ["Post 1"]
    assert rec.marked_published == [1]


def test_nothing_due_publishes_nothing(monkeypatch):
    rec = Recorder(monkeypatch, [[]])
    background_scheduler.check_schedules()
    assert rec.published_texts == []
    assert rec.marked_published == []


def test_publish_failure_is_marked_failed(monkeypatch):
    rec = Recorder(monkeypatch, [[make_post(2)]], publish_result="Publishing failed: HTTP 500")
    background_scheduler.check_schedules()
    assert rec.marked_published == []
    assert rec.marked_failed == [(2, "Publishing failed: HTTP 500")]


def test_missing_credentials_marks_failed_without_publishing(monkeypatch):
    rec = Recorder(monkeypatch, [[make_post(3)]], credentials=False)
    background_scheduler.check_schedules()
    assert rec.published_texts == []
    assert rec.marked_published == []
    assert len(rec.marked_failed) == 1
    assert rec.marked_failed[0][0] == 3