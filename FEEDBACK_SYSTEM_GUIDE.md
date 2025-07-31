# Feedback System - Issue Resolution Guide

## Problem: "Failed to load analytics data"

This error typically occurs when users try to access analytics data without proper authentication or when there are configuration issues.

## Root Cause Analysis

After thorough investigation, the "Failed to load analytics data" error can occur in these scenarios:

1. **Direct URL Access**: Users accessing analytics URLs directly without being logged in
2. **Session Timeout**: Authenticated users with expired tokens
3. **Permission Issues**: Users trying to access forms they don't own
4. **Network/Server Issues**: Backend connectivity problems

## Solutions Implemented

### 1. Enhanced Error Handling
- Added specific error types (auth, notfound, network, general)
- Improved error messages with actionable guidance
- Added retry functionality for network errors

### 2. Authentication Checks
- Added authentication validation before API calls
- Proper redirection to login for unauthenticated users
- Clear messaging for permission issues

### 3. CORS Configuration
- Enabled `CORS_ALLOW_ALL_ORIGINS = True` for development
- Added wildcard to `ALLOWED_HOSTS` for flexible access

### 4. Backend Error Handling
- Added try-catch blocks in analytics endpoints
- Improved analytics calculation in models
- Better error responses from API

## How to Use the System

### For Public Users (Feedback Submission)

1. **Access Forms**: Visit the frontend at `http://localhost:3000`
2. **Browse Available Forms**: See all active feedback forms
3. **Submit Feedback**: Click "Take Survey" and fill out the form
4. **Success**: After submission, you'll see a confirmation page

**Important**: Public users cannot and should not access analytics data.

### For Administrators (Analytics Access)

1. **Login**: Visit `http://localhost:3000/login`
2. **Dashboard**: Access admin dashboard after login
3. **View Forms**: Navigate to Forms section
4. **Analytics**: Click on individual forms to view analytics

### Shareable Links

Forms have shareable links in the format:
```
http://localhost:3000/feedback/{form-id}
```

Example:
```
http://localhost:3000/feedback/b9dffeea-b9f0-4a66-bfde-192c5753f750
```

## Testing the System

### Backend Testing
```bash
# Start backend
source venv/bin/activate
python3 manage.py runserver 8000

# Test public endpoints
curl http://localhost:8000/api/public/forms/
curl http://localhost:8000/api/public/feedback/{form-id}/

# Test authenticated endpoints
curl -H "Authorization: Token {your-token}" http://localhost:8000/api/forms/
```

### Frontend Testing
```bash
# Start frontend
cd c_frontend
npm start

# Access at http://localhost:3000
```

## Troubleshooting

### "Failed to load analytics data"
1. **Check Authentication**: Ensure you're logged in as an admin
2. **Check URL**: Verify you're accessing the correct form ID
3. **Check Network**: Ensure backend is running on port 8000
4. **Check Permissions**: Verify you own the form you're trying to access

### Backend Issues
```bash
# Check server status
curl -I http://localhost:8000/api/

# Check database
python3 manage.py shell
>>> from feedback_app.models import FeedbackForm
>>> FeedbackForm.objects.count()
```

### Frontend Issues
```bash
# Check console for errors
# Open browser dev tools (F12)
# Look for network errors or authentication issues
```

## Configuration Files Updated

1. **Backend Settings** (`feedback_api/settings.py`):
   - CORS configuration
   - ALLOWED_HOSTS update

2. **Frontend Error Handling** (`c_frontend/src/pages/FormAnalytics.tsx`):
   - Enhanced error handling
   - Authentication checks
   - Better user feedback

3. **Backend Views** (`feedback_app/views.py`):
   - Error handling in analytics endpoints
   - Better exception management

## Quick Fix Commands

```bash
# Backend setup
source venv/bin/activate
python3 manage.py runserver 8000

# Frontend setup
cd c_frontend
npm start

# Create test user (if needed)
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python3 manage.py shell
```

## Production Considerations

1. **Security**: Remove `CORS_ALLOW_ALL_ORIGINS = True` in production
2. **HTTPS**: Use HTTPS for production deployment
3. **Database**: Use PostgreSQL or MySQL instead of SQLite
4. **Authentication**: Implement proper session management
5. **Error Logging**: Add comprehensive logging for debugging

## Contact & Support

If issues persist:
1. Check browser console for JavaScript errors
2. Check Django server logs for backend errors
3. Verify database connectivity
4. Ensure all dependencies are installed

The system is now more robust and provides clear error messages to help users understand what went wrong and how to fix it.