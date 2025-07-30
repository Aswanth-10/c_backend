from django.contrib import admin
from .models import FeedbackForm, Question, FeedbackResponse, Answer, FormAnalytics, Notification


@admin.register(FeedbackForm)
class FeedbackFormAdmin(admin.ModelAdmin):
    list_display = ['title', 'form_type', 'created_by', 'created_at', 'is_active', 'response_count']
    list_filter = ['form_type', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'response_count']
    date_hierarchy = 'created_at'
    
    def response_count(self, obj):
        return obj.response_count
    response_count.short_description = 'Responses'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'form', 'question_type', 'is_required', 'order']
    list_filter = ['question_type', 'is_required', 'form']
    search_fields = ['text', 'form__title']
    ordering = ['form', 'order']


@admin.register(FeedbackResponse)
class FeedbackResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'form', 'submitted_at', 'ip_address']
    list_filter = ['submitted_at', 'form']
    search_fields = ['form__title']
    readonly_fields = ['id', 'submitted_at']
    date_hierarchy = 'submitted_at'


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['response', 'question', 'answer_text']
    list_filter = ['question__question_type']
    search_fields = ['answer_text', 'question__text', 'response__form__title']


@admin.register(FormAnalytics)
class FormAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['form', 'total_responses', 'completion_rate', 'average_rating', 'last_updated']
    list_filter = ['last_updated']
    readonly_fields = ['total_responses', 'completion_rate', 'average_rating', 'last_updated']
    
    def has_add_permission(self, request):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
