from rest_framework import serializers
from .models import FeedbackForm, Question, FeedbackResponse, Answer, FormAnalytics, Notification


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'is_required', 'order', 'options']


class FeedbackFormSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    response_count = serializers.ReadOnlyField()
    shareable_link = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = FeedbackForm
        fields = [
            'id', 'title', 'description', 'form_type', 'created_by', 
            'created_at', 'updated_at', 'is_active', 'expires_at',
            'questions', 'response_count', 'shareable_link', 'is_expired'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class FeedbackFormCreateSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)
    
    class Meta:
        model = FeedbackForm
        fields = [
            'title', 'description', 'form_type', 'is_active', 
            'expires_at', 'questions'
        ]
    
    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        validated_data['created_by'] = self.context['request'].user
        form = FeedbackForm.objects.create(**validated_data)
        
        for i, question_data in enumerate(questions_data):
            question_data['order'] = i
            Question.objects.create(form=form, **question_data)
        
        return form


class AnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    
    class Meta:
        model = Answer
        fields = ['id', 'question', 'question_text', 'question_type', 'answer_text', 'answer_value']


class FeedbackResponseSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    form_title = serializers.CharField(source='form.title', read_only=True)
    
    class Meta:
        model = FeedbackResponse
        fields = ['id', 'form', 'form_title', 'submitted_at', 'answers']
        read_only_fields = ['id', 'submitted_at']


class FeedbackResponseCreateSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True)
    
    class Meta:
        model = FeedbackResponse
        fields = ['form', 'answers']
    
    def create(self, validated_data):
        answers_data = validated_data.pop('answers', [])
        
        # Get client IP and user agent
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        response = FeedbackResponse.objects.create(**validated_data)
        
        for answer_data in answers_data:
            Answer.objects.create(response=response, **answer_data)
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FormAnalyticsSerializer(serializers.ModelSerializer):
    form_title = serializers.CharField(source='form.title', read_only=True)
    
    class Meta:
        model = FormAnalytics
        fields = [
            'id', 'form', 'form_title', 'total_responses', 
            'completion_rate', 'average_rating', 'last_updated'
        ]
        read_only_fields = ['id', 'total_responses', 'completion_rate', 'average_rating', 'last_updated']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 
            'is_read', 'created_at', 'data'
        ]
        read_only_fields = ['id', 'created_at']


class QuestionAnalyticsSerializer(serializers.Serializer):
    """Serializer for question-level analytics"""
    question_id = serializers.IntegerField()
    question_text = serializers.CharField()
    question_type = serializers.CharField()
    response_count = serializers.IntegerField()
    average_rating = serializers.FloatField(allow_null=True)
    answer_distribution = serializers.DictField()  # For multiple choice questions


class FormSummarySerializer(serializers.Serializer):
    """Serializer for form summary statistics"""
    total_forms = serializers.IntegerField()
    active_forms = serializers.IntegerField()
    total_responses = serializers.IntegerField()
    recent_responses = serializers.IntegerField()
    average_completion_rate = serializers.FloatField()
    recent_responses_list = serializers.ListField() 