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
        form = serializer.save()
        
        # Create analytics record
        FormAnalytics.objects.create(form=form)
        
        # Send notification
        send_notification_to_group(
            f"user_{self.request.user.id}",
            "form_created",
            f"Form '{form.title}' created successfully",
            {"form_id": str(form.id)}
        )
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get detailed analytics for a specific form"""
        try:
            form = self.get_object()
            analytics, created = FormAnalytics.objects.get_or_create(form=form)
            
            # Always update analytics before returning
            analytics.update_analytics()
            
            serializer = FormAnalyticsSerializer(analytics)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Failed to load analytics data: {str(e)}'}, 
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
                try:
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
                        # Calculate average rating with better error handling
                        valid_ratings = []
                        for answer in answers:
                            try:
                                rating_value = float(answer.answer_text.strip())
                                if 0 <= rating_value <= 10:
                                    valid_ratings.append(rating_value)
                            except (ValueError, TypeError):
                                continue
                        
                        if valid_ratings:
                            analytics_data['average_rating'] = sum(valid_ratings) / len(valid_ratings)
                    
                    elif question.question_type in ['radio', 'checkbox', 'yes_no']:
                        # Calculate distribution
                        distribution = {}
                        for answer in answers:
                            answer_text = answer.answer_text.strip() if answer.answer_text else 'No Answer'
                            distribution[answer_text] = distribution.get(answer_text, 0) + 1
                        analytics_data['answer_distribution'] = distribution
                    
                    question_analytics.append(analytics_data)
                    
                except Exception as question_error:
                    # Log error but continue with other questions
                    print(f"Error processing question {question.id}: {str(question_error)}")
                    continue
            
            serializer = QuestionAnalyticsSerializer(question_analytics, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to load question analytics: {str(e)}'}, 
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
            
            # Get submitted answers
            submitted_answers = request.data.get('answers', [])
            
            if not submitted_answers:
                return Response(
                    {'error': 'No answers provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate that all required questions are answered
            required_questions = form.questions.filter(is_required=True)
            required_question_ids = set(required_questions.values_list('id', flat=True))
            submitted_question_ids = set()
            
            # Extract question IDs from submitted answers
            for answer_data in submitted_answers:
                if 'question' in answer_data or 'question_id' in answer_data:
                    question_id = answer_data.get('question') or answer_data.get('question_id')
                    if question_id:
                        try:
                            submitted_question_ids.add(int(question_id))
                        except (ValueError, TypeError):
                            pass
            
            # Check if all required questions are answered
            missing_required = required_question_ids - submitted_question_ids
            if missing_required:
                return Response(
                    {'error': 'Please answer all required questions'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create response
            response_data = {
                'form': form.id,
                'answers': submitted_answers
            }
            
            # Add IP address and user agent if available
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            serializer = FeedbackResponseCreateSerializer(
                data=response_data, 
                context={'request': request, 'ip_address': ip_address, 'user_agent': user_agent}
            )
            
            if serializer.is_valid():
                try:
                    response = serializer.save()
                    
                    # Update analytics with error handling
                    try:
                        analytics, created = FormAnalytics.objects.get_or_create(form=form)
                        analytics.update_analytics()
                    except Exception as analytics_error:
                        # Log analytics error but don't fail the submission
                        print(f"Analytics update failed: {str(analytics_error)}")
                    
                    # Send real-time notification with error handling
                    try:
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
                    except Exception as notification_error:
                        # Log notification error but don't fail the submission
                        print(f"Notification failed: {str(notification_error)}")
                    
                    return Response({
                        'message': 'Feedback submitted successfully',
                        'response_id': str(response.id),
                        'success': True
                    }, status=status.HTTP_201_CREATED)
                    
                except Exception as save_error:
                    return Response(
                        {'error': f'Failed to save feedback: {str(save_error)}'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Return validation errors
            return Response({
                'error': 'Invalid feedback data',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except FeedbackForm.DoesNotExist:
            return Response(
                {'error': 'Form not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to submit feedback: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


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
        try:
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
            
            # Calculate average completion rate with error handling
            try:
                analytics = FormAnalytics.objects.filter(form__created_by=user)
                if analytics.exists():
                    completion_rates = [a.completion_rate for a in analytics if a.completion_rate is not None]
                    avg_completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0.0
                else:
                    avg_completion_rate = 0.0
            except Exception as e:
                print(f"Error calculating completion rate: {str(e)}")
                avg_completion_rate = 0.0
            
            # Get recent responses for timeline with error handling
            try:
                recent_response_data = FeedbackResponse.objects.filter(
                    form__created_by=user
                ).select_related('form').order_by('-submitted_at')[:10]
                
                recent_responses_list = []
                for response in recent_response_data:
                    try:
                        recent_responses_list.append({
                            'id': str(response.id),
                            'form_title': response.form.title,
                            'submitted_at': response.submitted_at,
                            'form_id': str(response.form.id)
                        })
                    except Exception as response_error:
                        print(f"Error processing response {response.id}: {str(response_error)}")
                        continue
            except Exception as e:
                print(f"Error fetching recent responses: {str(e)}")
                recent_responses_list = []
            
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
            
        except Exception as e:
            return Response(
                {'error': f'Failed to load dashboard data: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
