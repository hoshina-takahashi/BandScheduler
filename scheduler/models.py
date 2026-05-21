from django.db import models
import uuid

class Group(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Schedule(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user_name = models.CharField(max_length=50)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    label = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user_name} / {self.date} {self.start_time}〜{self.end_time}"

# Create your models here.
