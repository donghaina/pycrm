import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer
from .db import SessionLocal, init_db
from .models import Deal, ProcessedEvent

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "redpanda:9092")
TOPIC = "deal.review.requested"


def _to_uuid(value: str | uuid.UUID | None, field_name: str) -> uuid.UUID:
    if value is None:
        raise ValueError(f"Missing {field_name}")
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


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
        if float(deal.amount) < 10000:
            deal.review_status = "APPROVED"
            deal.review_score = 90
            deal.review_reason = "Auto-approved"
        else:
            deal.review_status = "REJECTED"
            deal.review_score = 40
            deal.review_reason = "Amount exceeds auto-approval threshold"

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


async def main():
    init_db()

    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BROKERS,
        group_id="review-worker",
        auto_offset_reset="earliest",
    )

    await consumer.start()
    try:
        async for msg in consumer:
            payload = json.loads(msg.value.decode("utf-8"))
            await process_message(payload)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())