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
    """Serializer for creating feedback responses"""
    answers = AnswerCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = FeedbackResponse
        fields = ['form', 'answers']
    
    def create(self, validated_data):
        answers_data = validated_data.pop('answers')
        
        # Get additional data from context
        context = self.context
        ip_address = context.get('ip_address')
        user_agent = context.get('user_agent', '')
        
        # Create the response with additional data
        response = FeedbackResponse.objects.create(
            form=validated_data['form'],
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Create answers with better error handling
        created_answers = []
        for answer_data in answers_data:
            try:
                answer = Answer.objects.create(
                    response=response,
                    question=answer_data['question'],
                    answer_text=answer_data.get('answer_text', ''),
                    answer_value=answer_data.get('answer_value', {})
                )
                created_answers.append(answer)
            except Exception as e:
                # Log the error but continue with other answers
                print(f"Error creating answer: {str(e)}")
                continue
        
        if not created_answers:
            # If no answers were created, delete the response and raise error
            response.delete()
            raise serializers.ValidationError("Failed to create any answers for this response")
        
        return response


class AnswerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating answers"""
    
    class Meta:
        model = Answer
        fields = ['question', 'answer_text', 'answer_value']
    
    def validate(self, data):
        """Validate answer data"""
        question = data.get('question')
        answer_text = data.get('answer_text', '')
        
        if not question:
            raise serializers.ValidationError("Question is required")
        
        # Validate required answers
        if question.is_required and not answer_text.strip():
            raise serializers.ValidationError(f"Answer is required for question: {question.text}")
        
        # Validate rating values
        if question.question_type in ['rating', 'rating_10']:
            try:
                rating_value = float(answer_text.strip())
                max_rating = 10 if question.question_type == 'rating_10' else 5
                if not (1 <= rating_value <= max_rating):
                    raise serializers.ValidationError(f"Rating must be between 1 and {max_rating}")
            except (ValueError, TypeError):
                if answer_text.strip():  # Only validate if answer is provided
                    raise serializers.ValidationError("Rating must be a valid number")
        
        # Validate email format
        if question.question_type == 'email' and answer_text.strip():
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, answer_text.strip()):
                raise serializers.ValidationError("Please enter a valid email address")
        
        return data


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