from django.db import models
from django.core.validators import FileExtensionValidator
import uuid
import json


class Candidate(models.Model):
    """Model to store candidate information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    resume = models.FileField(
        upload_to='resumes/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx'])],
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Interview status
    INTERVIEW_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    ]
    interview_status = models.CharField(max_length=20, choices=INTERVIEW_STATUS_CHOICES, default='pending')
    
    # Final scores and summary
    total_score = models.FloatField(default=0.0)
    ai_summary = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name or 'Unnamed'} - {self.email or 'No email'}"

    class Meta:
        ordering = ['-total_score', '-created_at']


class InterviewSession(models.Model):
    """Model to store interview session data"""
    candidate = models.OneToOneField(Candidate, on_delete=models.CASCADE, related_name='session')
    current_question_number = models.IntegerField(default=0)
    is_active = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    
    # Store session state for recovery
    session_data = models.JSONField(default=dict)
    
    def __str__(self):
        return f"Interview for {self.candidate.name or 'Unnamed'}"


class Question(models.Model):
    """Model to store interview questions and answers"""
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='questions')
    question_number = models.IntegerField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    question_text = models.TextField()
    answer_text = models.TextField(blank=True)
    time_allocated = models.IntegerField()  # in seconds
    time_taken = models.IntegerField(default=0)  # in seconds
    score = models.FloatField(default=0.0)
    ai_feedback = models.TextField(blank=True)
    asked_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['question_number']
        unique_together = ['session', 'question_number']
    
    def __str__(self):
        return f"Q{self.question_number} ({self.difficulty}) - {self.session.candidate.name or 'Unnamed'}"


class ChatMessage(models.Model):
    """Model to store chat messages during interview"""
    MESSAGE_TYPES = [
        ('system', 'System'),
        ('question', 'Question'),
        ('answer', 'Answer'),
        ('info', 'Information'),
        ('error', 'Error'),
    ]
    
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)  # Store additional data like timers, etc.
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."