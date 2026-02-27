from django.db import models


class Company(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.TextField()
    parent_id = models.UUIDField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'org"."companies'


class User(models.Model):
    id = models.UUIDField(primary_key=True)
    email = models.TextField()
    company_id = models.UUIDField()
    role = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'org"."users'
