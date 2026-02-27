import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer
from .db import SessionLocal, init_db
from .models import Deal, ProcessedEvent

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "redpanda:9092")
TOPIC = "deal.review.requested"
MAX_RETRIES = int(os.getenv("REVIEW_WORKER_MAX_RETRIES", "3"))
RETRY_BACKOFF_SEC = float(os.getenv("REVIEW_WORKER_RETRY_BACKOFF_SEC", "0.5"))

logger = logging.getLogger("review-worker")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def _to_uuid(value: str | uuid.UUID | None, field_name: str) -> uuid.UUID:
    if value is None:
        raise ValueError(f"Missing {field_name}")
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def get_review_decision(amount: float) -> tuple[str, int, str]:
    if float(amount) < 10000:
        return "APPROVED", 90, "Auto-approved"
    return "REJECTED", 40, "Amount exceeds auto-approval threshold"


def record_failure(
    event_id: uuid.UUID | None,
    error: str,
    attempt_count: int = 0,
    error_type: str | None = None,
    error_stage: str | None = None,
):
    if not event_id:
        return
    db = SessionLocal()
    try:
        existing = db.query(ProcessedEvent).filter(
            ProcessedEvent.event_id == event_id
        ).first()
        if existing:
            return
        db.add(
            ProcessedEvent(
                event_id=event_id,
                topic=TOPIC,
                status="FAILED",
                error=error[:500],
                error_type=error_type,
                error_stage=error_stage,
                attempt_count=attempt_count,
            )
        )
        db.commit()
    finally:
        db.close()


async def process_message(payload: dict):
    # ⭐ 核心：第一时间把字符串 ID 转成 UUID
    event_id = _to_uuid(payload.get("event_id"), "event_id")
    deal_id = _to_uuid(payload.get("deal_id"), "deal_id")

    db = SessionLocal()
    try:
        # 幂等检查
        existing = db.query(ProcessedEvent).filter(
            ProcessedEvent.event_id == event_id
        ).first()
        if existing:
            return

        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            db.add(
                ProcessedEvent(
                    event_id=event_id,
                    topic=TOPIC,
                    status="FAILED",
                    error="Deal not found",
                )
            )
            db.commit()
            return

        # 简单审批规则
        status, score, reason = get_review_decision(float(deal.amount))
        deal.review_status = status
        deal.review_score = score
        deal.review_reason = reason

        deal.reviewed_at = datetime.now(timezone.utc)
        deal.stage = deal.review_status
        deal.version = deal.version + 1

        db.add(
            ProcessedEvent(
                event_id=event_id,
                topic=TOPIC,
                status="PROCESSED",
            )
        )
        db.commit()

    finally:
        db.close()


async def process_with_retries(
    payload: dict,
    process_fn= None,
    max_retries: int | None = None,
    backoff_sec: float | None = None,
    sleep= None,
    record_failure_fn= None,
):
    if process_fn is None:
        process_fn = process_message
    if max_retries is None:
        max_retries = MAX_RETRIES
    if backoff_sec is None:
        backoff_sec = RETRY_BACKOFF_SEC
    if sleep is None:
        sleep = asyncio.sleep
    if record_failure_fn is None:
        record_failure_fn = record_failure

    event_id = None
    try:
        event_id = _to_uuid(payload.get("event_id"), "event_id")
    except Exception:
        logger.exception("Invalid event payload: missing/invalid event_id")

    for attempt in range(1, max_retries + 1):
        try:
            await process_fn(payload)
            return True
        except Exception as exc:
            logger.exception("Error processing event (attempt %s/%s)", attempt, max_retries)
            if attempt >= max_retries:
                record_failure_fn(
                    event_id,
                    str(exc),
                    attempt_count=attempt,
                    error_type=exc.__class__.__name__,
                    error_stage="process_message",
                )
                return False
            await sleep(backoff_sec)


async def main():
    init_db()

    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BROKERS,
        group_id="review-worker",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )

    await consumer.start()
    try:
        async for msg in consumer:
            payload = json.loads(msg.value.decode("utf-8"))
            await process_with_retries(payload)
            await consumer.commit()
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())
