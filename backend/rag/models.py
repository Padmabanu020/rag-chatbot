from django.db import models


class Document(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/")
    file_type = models.CharField(max_length=10)
    chunk_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="processing")  # processing | ready | failed
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ChatMessage(models.Model):
    question = models.TextField()
    answer = models.TextField()
    sources = models.TextField(default="[]")  # JSON list of cited chunks
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
