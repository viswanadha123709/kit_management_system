from django.db import models

class kit(models.Model):
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    items = models.JSONField()


class schedule(models.Model):
    kit_id = models.CharField(max_length=100, unique=True)
    user_id=models.IntegerField()
    start = models.DateTimeField()
    end = models.DateTimeField()


class instrument(models.Model):
    instrument_name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100)
    specifiations = models.CharField(max_length=500,blank=True)
    working = models.BooleanField(default=True)


class user(models.Model):
    user_name = models.CharField(max_length=100)
    user_age = models.IntegerField()
    user_number = models.IntegerField()
    user_adhar = models.IntegerField()