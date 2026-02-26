# review-worker

Kafka consumer for `deal.review.requested`.

Responsibilities:
- Idempotent processing (processed_events table)
- Update deal review_status
- Retry/DLQ policy
