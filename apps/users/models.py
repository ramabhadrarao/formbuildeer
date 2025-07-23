from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    department = models.CharField(max_length=100, blank=True)
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    class Meta:
        db_table = 'users'