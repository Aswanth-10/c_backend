from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class FeedbackForm(models.Model):
    """Model for storing feedback form templates"""
    FORM_TYPES = [
        ('customer_satisfaction', 'Customer Satisfaction'),
        ('employee_feedback', 'Employee Feedback'),
        ('product_feedback', 'Product Feedback'),
        ('service_feedback', 'Service Feedback'),
        ('general', 'General Feedback'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    form_type = models.CharField(max_length=50, choices=FORM_TYPES, default='general')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_forms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def response_count(self):
        return self.responses.count()
    
    @property
    def shareable_link(self):
        return f"/feedback/{self.id}/"


class Question(models.Model):
    """Model for storing questions within feedback forms"""
    QUESTION_TYPES = [
        ('text', 'Text Input'),
        ('textarea', 'Long Text'),
        ('radio', 'Single Choice'),
        ('checkbox', 'Multiple Choice'),
        ('rating', 'Rating (1-5)'),
        ('rating_10', 'Rating (1-10)'),
        ('yes_no', 'Yes/No'),
        ('email', 'Email'),
        ('phone', 'Phone Number'),
    ]
    
    form = models.ForeignKey(FeedbackForm, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    options = models.JSONField(default=list, blank=True)  # For radio/checkbox questions
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.form.title} - {self.text[:50]}"


class FeedbackResponse(models.Model):
    """Model for storing individual feedback responses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form = models.ForeignKey(FeedbackForm, on_delete=models.CASCADE, related_name='responses')
    submitted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Response to {self.form.title} - {self.submitted_at}"


class Answer(models.Model):
    """Model for storing answers to individual questions"""
    response = models.ForeignKey(FeedbackResponse, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField()
    answer_value = models.JSONField(default=dict, blank=True)  # For structured answers
    
    class Meta:
        unique_together = ['response', 'question']
    
    def __str__(self):
        return f"Answer to {self.question.text[:30]}"


class FormAnalytics(models.Model):
    """Model for storing analytics data for forms"""
    form = models.OneToOneField(FeedbackForm, on_delete=models.CASCADE, related_name='analytics')
    total_responses = models.PositiveIntegerField(default=0)
    completion_rate = models.FloatField(default=0.0)  # Percentage
    average_rating = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics for {self.form.title}"
    
    def update_analytics(self):
        """Update analytics based on current responses"""
        try:
            responses = self.form.responses.all()
            self.total_responses = responses.count()
            
            if self.total_responses > 0:
                # Calculate completion rate - fixed the query
                total_questions = self.form.questions.count()
                if total_questions > 0:
                    # Count responses that have answers for all questions
                    completed_responses = 0
                    for response in responses:
                        if response.answers.count() == total_questions:
                            completed_responses += 1
                    self.completion_rate = (completed_responses / self.total_responses) * 100
                else:
                    self.completion_rate = 100.0  # If no questions, consider it complete
                
                # Calculate average rating - improved error handling
                rating_answers = Answer.objects.filter(
                    response__form=self.form,
                    question__question_type__in=['rating', 'rating_10']
                )
                if rating_answers.exists():
                    valid_ratings = []
                    for ans in rating_answers:
                        try:
                            # More robust numeric validation
                            rating_value = float(ans.answer_text.strip())
                            if 0 <= rating_value <= 10:  # Valid rating range
                                valid_ratings.append(rating_value)
                        except (ValueError, TypeError):
                            continue  # Skip invalid ratings
                    
                    if valid_ratings:
                        self.average_rating = sum(valid_ratings) / len(valid_ratings)
                    else:
                        self.average_rating = 0.0
                else:
                    self.average_rating = 0.0
            else:
                self.completion_rate = 0.0
                self.average_rating = 0.0
            
            self.save()
            
        except Exception as e:
            # Log the error and set default values
            print(f"Error updating analytics for form {self.form.id}: {str(e)}")
            self.total_responses = 0
            self.completion_rate = 0.0
            self.average_rating = 0.0
            self.save()


class Notification(models.Model):
    """Model for storing real-time notifications"""
    NOTIFICATION_TYPES = [
        ('new_response', 'New Response'),
        ('form_created', 'Form Created'),
        ('form_updated', 'Form Updated'),
        ('analytics_update', 'Analytics Update'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(default=dict, blank=True)  # Additional data
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} - {self.title}"
