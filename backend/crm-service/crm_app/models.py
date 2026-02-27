from django.db import models
from django.utils import timezone


class Deal(models.Model):
    id = models.UUIDField(primary_key=True)
    child_company_id = models.UUIDField()
    title = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.TextField()
    stage = models.TextField()
    review_status = models.TextField()
    review_score = models.IntegerField(null=True, blank=True)
    review_reason = models.TextField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.UUIDField()
    version = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'crm"."deals'


class ProcessedEvent(models.Model):
    event_id = models.UUIDField(primary_key=True)
    topic = models.TextField()
    status = models.TextField()
    error = models.TextField(null=True, blank=True)
    processed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'crm"."processed_events'
