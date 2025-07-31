from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'forms', views.FeedbackFormViewSet, basename='feedbackform')
router.register(r'responses', views.FeedbackResponseViewSet, basename='feedbackresponse')
router.register(r'notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
    # Admin dashboard
    path('', views.admin_dashboard, name='admin_dashboard'),
    
    # Public form template
    path('feedback/<uuid:form_id>/', views.public_form, name='public_form'),
    
    # Authentication endpoints
    path('api/auth/login/', views.CustomAuthToken.as_view(), name='auth_login'),
    path('api/auth/logout/', views.LogoutView.as_view(), name='auth_logout'),
    path('api/auth/user/', views.CurrentUserView.as_view(), name='auth_user'),
    
    # API endpoints
    path('api/', include(router.urls)),
    
    # Dashboard and statistics
    path('api/dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('api/stats/', views.FormStatsView.as_view(), name='form_stats'),
    path('api/form-types/', views.FormTypesView.as_view(), name='form_types'),
    
    # Public feedback form endpoints
    path('api/public/forms/', views.PublicFormsListView.as_view(), name='public_forms_list'),
    path('api/public/feedback/<uuid:form_id>/', views.PublicFeedbackFormView.as_view(), name='public_feedback_form'),
] 