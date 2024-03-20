from django.db import models
from django.contrib.auth.models import AbstractUser

class Network(models.Model):
    id = models.AutoField(primary_key=True)
    location = models.CharField(max_length=100)

    def __str__(self):
        return self.location
    
# Create your models here.
class Item(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='items')
    charge_point_id = models.CharField(max_length=100)

    def __str__(self):
        return f"Item {self.id} ({self.status})"

class Transaction(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('finished', 'Finished'),
    ]

    id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')
    charger = models.ForeignKey(Item, on_delete=models.CASCADE, related_name ='transactions')
