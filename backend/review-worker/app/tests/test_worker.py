import asyncio
import uuid
from unittest import TestCase
from unittest.mock import patch

from app.worker import get_review_decision
from app.worker import process_message
from app.worker import process_with_retries
from app.models import ProcessedEvent


class TestReviewDecision(TestCase):
    def test_auto_approved_for_small_amount(self):
        status, score, reason = get_review_decision(9999.99)
        self.assertEqual(status, "APPROVED")
        self.assertEqual(score, 90)
        self.assertEqual(reason, "Auto-approved")

    def test_rejected_for_large_amount(self):
        status, score, reason = get_review_decision(10000)
        self.assertEqual(status, "REJECTED")
        self.assertEqual(score, 40)
        self.assertEqual(reason, "Amount exceeds auto-approval threshold")


class FakeQuery:
    def __init__(self, result):
        self._result = result
        self.filtered = False

    def filter(self, *args, **kwargs):
        self.filtered = True
        return self

    def first(self):
        return self._result


class FakeSession:
    def __init__(self, existing_event):
        self.existing_event = existing_event
        self.added = []
        self.committed = False
        self.closed = False
        self.queries = []

    def query(self, model):
        self.queries.append(model)
        if model is ProcessedEvent:
            return FakeQuery(self.existing_event)
        return FakeQuery(None)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class TestIdempotency(TestCase):
    @patch("app.worker.SessionLocal")
    def test_duplicate_event_is_ignored(self, mock_session_local):
        event_id = uuid.uuid4()
        existing = ProcessedEvent(
            event_id=event_id,
            topic="deal.review.requested",
            status="PROCESSED",
        )
        fake_session = FakeSession(existing)
        mock_session_local.return_value = fake_session

        payload = {
            "event_id": str(event_id),
            "deal_id": str(uuid.uuid4()),
        }

        asyncio.run(process_message(payload))

        self.assertEqual(fake_session.added, [])
        self.assertFalse(fake_session.committed)
        self.assertIn(ProcessedEvent, fake_session.queries)
        self.assertTrue(fake_session.closed)


class TestRetries(TestCase):
    def test_retry_and_record_failure(self):
        event_id = uuid.uuid4()
        payload = {
            "event_id": str(event_id),
            "deal_id": str(uuid.uuid4()),
        }

        calls = {"attempts": 0, "sleeps": 0, "failures": []}

        async def failing_process(_payload):
            calls["attempts"] += 1
            raise RuntimeError("boom")

        async def fake_sleep(_sec):
            calls["sleeps"] += 1

        def fake_record_failure(eid, err, attempt_count=0, error_type=None, error_stage=None):
            calls["failures"].append((eid, err, attempt_count, error_type, error_stage))

        result = asyncio.run(
            process_with_retries(
                payload,
                process_fn=failing_process,
                max_retries=3,
                backoff_sec=0,
                sleep=fake_sleep,
                record_failure_fn=fake_record_failure,
            )
        )

        self.assertFalse(result)
        self.assertEqual(calls["attempts"], 3)
        self.assertEqual(calls["sleeps"], 2)
        self.assertEqual(len(calls["failures"]), 1)
        self.assertEqual(calls["failures"][0][0], event_id)
        self.assertEqual(calls["failures"][0][2], 3)
        self.assertEqual(calls["failures"][0][3], "RuntimeError")
        self.assertEqual(calls["failures"][0][4], "process_message")

    def test_success_stops_retries(self):
        event_id = uuid.uuid4()
        payload = {
            "event_id": str(event_id),
            "deal_id": str(uuid.uuid4()),
        }

        calls = {"attempts": 0, "sleeps": 0, "failures": 0}

        async def flaky_process(_payload):
            calls["attempts"] += 1
            if calls["attempts"] == 1:
                raise RuntimeError("first failure")

        async def fake_sleep(_sec):
            calls["sleeps"] += 1

        def fake_record_failure(*_args, **_kwargs):
            calls["failures"] += 1

        result = asyncio.run(
            process_with_retries(
                payload,
                process_fn=flaky_process,
                max_retries=3,
                backoff_sec=0,
                sleep=fake_sleep,
                record_failure_fn=fake_record_failure,
            )
        )

        self.assertTrue(result)
        self.assertEqual(calls["attempts"], 2)
        self.assertEqual(calls["sleeps"], 1)
        self.assertEqual(calls["failures"], 0)
