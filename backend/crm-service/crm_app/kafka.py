import asyncio
import json
import os
from aiokafka import AIOKafkaProducer


async def _publish_event(topic: str, payload: dict):
    brokers = os.getenv("KAFKA_BROKERS", "redpanda:9092")
    producer = AIOKafkaProducer(bootstrap_servers=brokers)
    await producer.start()
    try:
        await producer.send_and_wait(topic, json.dumps(payload).encode("utf-8"))
    finally:
        await producer.stop()


def publish_event(topic: str, payload: dict):
    asyncio.run(_publish_event(topic, payload))
