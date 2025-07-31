from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
import json

from .models import (
    FeedbackForm, Question, FeedbackResponse, Answer, 
    FormAnalytics, Notification
)
from .serializers import (
    FeedbackFormSerializer, FeedbackFormCreateSerializer,
    FeedbackResponseSerializer, FeedbackResponseCreateSerializer,
    FormAnalyticsSerializer, NotificationSerializer,
    QuestionAnalyticsSerializer, FormSummarySerializer
)
from .consumers import send_notification_to_group

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from django.contrib.auth import logout as django_logout


class FeedbackFormViewSet(viewsets.ModelViewSet):
    """ViewSet for managing feedback forms"""
    queryset = FeedbackForm.objects.all()
    serializer_class = FeedbackFormSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return FeedbackForm.objects.filter(created_by=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FeedbackFormCreateSerializer
        return FeedbackFormSerializer
    
    def perform_create(self, serializer):
        form = serializer.save(created_by=self.request.user)
        
        # Create analytics record
        try:
            analytics, created = FormAnalytics.objects.get_or_create(form=form)
            if created:
                analytics.update_analytics()
        except Exception as e:
            print(f"Warning: Could not create analytics for form {form.id}: {e}")
        
        # Send notification (optional, skip if websocket not available)
        try:
            send_notification_to_group(
                f"user_{self.request.user.id}",
                "form_created",
                f"Form '{form.title}' created successfully",
                {"form_id": str(form.id)}
            )
        except Exception as e:
            print(f"Warning: Could not send notification: {e}")
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get detailed analytics for a specific form"""
        try:
            form = self.get_object()
            analytics, created = FormAnalytics.objects.get_or_create(form=form)
            analytics.update_analytics()
            
            serializer = FormAnalyticsSerializer(analytics)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Unable to load analytics: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def question_analytics(self, request, pk=None):
        """Get analytics for individual questions"""
        try:
            form = self.get_object()
            questions = form.questions.all()
            
            question_analytics = []
            for question in questions:
                answers = Answer.objects.filter(question=question)
                response_count = answers.count()
                
                analytics_data = {
                    'question_id': question.id,
                    'question_text': question.text,
                    'question_type': question.question_type,
                    'response_count': response_count,
                    'average_rating': None,
                    'answer_distribution': {}
                }
                
                if question.question_type in ['rating', 'rating_10']:
                    avg_rating = answers.filter(answer_text__regex=r'^\d+$').aggregate(
                        avg=Avg('answer_text')
                    )['avg']
                    analytics_data['average_rating'] = float(avg_rating) if avg_rating else None
                
                elif question.question_type in ['radio', 'checkbox', 'yes_no']:
                    distribution = answers.values('answer_text').annotate(
                        count=Count('answer_text')
                    ).order_by('-count')
                    analytics_data['answer_distribution'] = {
                        item['answer_text']: item['count'] for item in distribution
                    }
                
                question_analytics.append(analytics_data)
            
            serializer = QuestionAnalyticsSerializer(question_analytics, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Unable to load question analytics: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def share_link(self, request, pk=None):
        """Get shareable link for the form"""
        form = self.get_object()
        return Response({
            'shareable_link': form.shareable_link,
            'form_id': str(form.id)
        })

class PublicFormsListView(APIView):
    """Public view for listing all active feedback forms"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get list of all active public forms"""
        forms = FeedbackForm.objects.filter(
            is_active=True
        ).order_by('-created_at')
        
        # Filter out expired forms
        active_forms = [form for form in forms if not form.is_expired]
        
        serializer = FeedbackFormSerializer(active_forms, many=True)
        return Response(serializer.data)


class PublicFeedbackFormView(APIView):
    """Public view for accessing feedback forms via shareable links"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, form_id):
        """Get form details for public access"""
        try:
            form = FeedbackForm.objects.get(id=form_id, is_active=True)
            
            # Check if form is expired
            if form.is_expired:
                return Response(
                    {'error': 'This form has expired'}, 
                    status=status.HTTP_410_GONE
                )
            
            serializer = FeedbackFormSerializer(form)
            return Response(serializer.data)
        
        except FeedbackForm.DoesNotExist:
            return Response(
                {'error': 'Form not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def post(self, request, form_id):
        """Submit a feedback response"""
        try:
            form = FeedbackForm.objects.get(id=form_id, is_active=True)
            
            # Check if form is expired
            if form.is_expired:
                return Response(
                    {'error': 'This form has expired'}, 
                    status=status.HTTP_410_GONE
                )
            
            # Validate that all required questions are answered
            required_questions = form.questions.filter(is_required=True)
            submitted_answers = request.data.get('answers', [])
            
            if len(submitted_answers) < required_questions.count():
                return Response(
                    {'error': 'Please answer all required questions'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create response
            response_data = {
                'form': form.id,
                'answers': submitted_answers
            }
            
            serializer = FeedbackResponseCreateSerializer(
                data=response_data, 
                context={'request': request}
            )
            
            if serializer.is_valid():
                response = serializer.save()
                
                # Update analytics
                analytics, created = FormAnalytics.objects.get_or_create(form=form)
                analytics.update_analytics()
                
                # Send real-time notification to form creator
                send_notification_to_group(
                    f"user_{form.created_by.id}",
                    "new_response",
                    f"New response received for '{form.title}'",
                    {
                        "form_id": str(form.id),
                        "response_id": str(response.id),
                        "form_title": form.title
                    }
                )
                
                return Response({
                    'message': 'Feedback submitted successfully',
                    'response_id': str(response.id)
                }, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except FeedbackForm.DoesNotExist:
            return Response(
                {'error': 'Form not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class FeedbackResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing feedback responses"""
    serializer_class = FeedbackResponseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return FeedbackResponse.objects.filter(form__created_by=self.request.user)


class DashboardView(APIView):
    """Dashboard view for admin overview"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get dashboard summary data"""
        user = request.user
        
        # Get user's forms
        forms = FeedbackForm.objects.filter(created_by=user)
        active_forms = forms.filter(is_active=True)
        
        # Get total responses
        total_responses = FeedbackResponse.objects.filter(form__created_by=user).count()
        
        # Get recent responses (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_responses = FeedbackResponse.objects.filter(
            form__created_by=user,
            submitted_at__gte=week_ago
        ).count()
        
        # Calculate average completion rate
        analytics = FormAnalytics.objects.filter(form__created_by=user)
        avg_completion_rate = analytics.aggregate(
            avg_rate=Avg('completion_rate')
        )['avg_rate'] or 0.0
        
        # Get recent responses for timeline
        recent_response_data = FeedbackResponse.objects.filter(
            form__created_by=user
        ).select_related('form').order_by('-submitted_at')[:10]
        
        recent_responses_list = [
            {
                'id': str(response.id),
                'form_title': response.form.title,
                'submitted_at': response.submitted_at,
                'form_id': str(response.form.id)
            }
            for response in recent_response_data
        ]
        
        summary_data = {
            'total_forms': forms.count(),
            'active_forms': active_forms.count(),
            'total_responses': total_responses,
            'recent_responses': recent_responses,
            'average_completion_rate': round(avg_completion_rate, 2),
            'recent_responses_list': recent_responses_list
        }
        
        serializer = FormSummarySerializer(summary_data)
        return Response(serializer.data)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for managing notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all marked as read'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})


class CustomAuthToken(ObtainAuthToken):
    """Custom authentication view that returns user data along with token"""
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
        })


class LogoutView(APIView):
    """Logout view to invalidate token"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Delete the token
            request.user.auth_token.delete()
        except:
            pass
        
        # Logout from Django session
        django_logout(request)
        
        return Response({'message': 'Successfully logged out'})


class CurrentUserView(APIView):
    """Get current user information"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        })
