from django.contrib import admin
from .models import Candidate, InterviewSession, Question, ChatMessage


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'interview_status', 'total_score', 'created_at')
    list_filter = ('interview_status', 'created_at')
    search_fields = ('name', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'current_question_number', 'is_active', 'started_at', 'completed_at')
    list_filter = ('is_active', 'started_at')
    readonly_fields = ('candidate',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('session', 'question_number', 'difficulty', 'score', 'asked_at')
    list_filter = ('difficulty', 'asked_at')
    readonly_fields = ('session', 'asked_at', 'answered_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'message_type', 'timestamp')
    list_filter = ('message_type', 'timestamp')
    readonly_fields = ('timestamp',)