from django.db import models
from django.utils import timezone

# Create your models here.

class Keyphrase(models.Model):
    phrase = models.CharField(max_length=250)
    # text = models.TextField()
    created_date = models.DateTimeField(
            default=timezone.now)

    def publish(self):
        self.save()

    def __str__(self):
        return self.phrase