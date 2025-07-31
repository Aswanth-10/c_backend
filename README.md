# Feedback Form Application

A Django-based feedback form application with admin-only access, enhanced analytics, and filtering capabilities.

## Features

### ✅ **Admin-Only Access**
- Removed user login functionality
- Only admin login is available
- Secure token-based authentication

### ✅ **Fixed Form Access Issue**
- Resolved "The requested form was not found or you don't have permission to view it" error
- Proper form validation and error handling
- Shareable links work correctly

### ✅ **Enhanced Analytics**
- Detailed form analytics with response trends
- Question-level analytics with response rates
- Visual charts for better data representation
- Daily response tracking
- Form type distribution analysis

### ✅ **Advanced Filtering**
- **Forms Section Filters:**
  - Form type filter
  - Active/Inactive status filter
  - Search by title/description
- **Responses Section Filters:**
  - Form type filter
  - Specific form filter
  - Date range filter (from/to)
  - Clear filters functionality

### ✅ **Improved Dashboard**
- Real-time statistics
- Response trends visualization
- Top performing forms
- Form type distribution charts

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create Admin User
```bash
python manage.py createsuperuser
```

### 4. Run the Server
```bash
python manage.py runserver
```

## Usage

### Admin Dashboard
1. Navigate to `http://localhost:8000/`
2. Login with your admin credentials
3. Access the dashboard with enhanced analytics and filtering

### Creating Forms
1. Go to the "Forms" section
2. Click "Create Form" (placeholder for future implementation)
3. Forms can be created via API or Django admin

### Sharing Forms
1. In the Forms section, click "Share" on any form
2. The shareable link will be copied to clipboard
3. Users can access the form via the shared link

### Public Form Access
- Users can fill out forms using shareable links
- No login required for form submission
- Forms are accessible at: `http://localhost:8000/feedback/{form_id}/`

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Admin login
- `POST /api/auth/logout/` - Logout
- `GET /api/auth/user/` - Get current user info

### Forms
- `GET /api/forms/` - List user's forms (with filtering)
- `POST /api/forms/` - Create new form
- `GET /api/forms/{id}/` - Get form details
- `PUT /api/forms/{id}/` - Update form
- `DELETE /api/forms/{id}/` - Delete form
- `GET /api/forms/{id}/analytics/` - Get form analytics
- `GET /api/forms/{id}/share_link/` - Get shareable link

### Responses
- `GET /api/responses/` - List responses (with filtering)
- `GET /api/responses/{id}/` - Get response details

### Analytics
- `GET /api/dashboard/` - Dashboard summary
- `GET /api/stats/` - Comprehensive statistics
- `GET /api/form-types/` - Available form types

### Public API
- `GET /api/public/forms/` - List public forms
- `GET /api/public/feedback/{form_id}/` - Get public form
- `POST /api/public/feedback/{form_id}/` - Submit response

## Filtering Parameters

### Forms Filtering
```
GET /api/forms/?form_type=customer_satisfaction&is_active=true&search=feedback
```

### Responses Filtering
```
GET /api/responses/?form_type=customer_satisfaction&form_id=uuid&date_from=2024-01-01&date_to=2024-12-31
```

## Form Types
- `customer_satisfaction` - Customer Satisfaction
- `employee_feedback` - Employee Feedback
- `product_feedback` - Product Feedback
- `service_feedback` - Service Feedback
- `general` - General Feedback

## Question Types
- `text` - Text Input
- `textarea` - Long Text
- `radio` - Single Choice
- `checkbox` - Multiple Choice
- `rating` - Rating (1-5)
- `rating_10` - Rating (1-10)
- `yes_no` - Yes/No
- `email` - Email
- `phone` - Phone Number

## Key Improvements Made

### 1. **Removed User Login**
- Only admin authentication is available
- Simplified user experience
- Secure admin-only access

### 2. **Fixed Form Access Issues**
- Proper error handling for form access
- Clear error messages
- Fixed shareable link functionality

### 3. **Enhanced Analytics**
- Question-level response rates
- Daily response trends
- Visual charts and graphs
- Top performing forms analysis
- Form type distribution

### 4. **Advanced Filtering**
- Multiple filter options for forms and responses
- Date range filtering
- Search functionality
- Clear filters option

### 5. **Improved UI/UX**
- Modern, responsive design
- Better data visualization
- Intuitive navigation
- Real-time updates

## File Structure

```
feedback_app/
├── models.py              # Database models
├── views.py               # API views and logic
├── serializers.py         # Data serialization
├── urls.py                # URL routing
├── templates/
│   └── feedback_app/
│       ├── index.html     # Admin dashboard
│       └── public_form.html # Public form template
└── ...

feedback_api/
├── settings.py            # Django settings
├── urls.py                # Main URL configuration
└── ...
```

## Troubleshooting

### Common Issues

1. **Form not found error**
   - Ensure the form is active
   - Check if the form has expired
   - Verify the form ID in the URL

2. **Authentication issues**
   - Clear browser cache and localStorage
   - Ensure you're using admin credentials
   - Check if the token is valid

3. **Analytics not loading**
   - Ensure forms have responses
   - Check browser console for errors
   - Verify API endpoints are accessible

## Future Enhancements

- Form creation interface in admin dashboard
- Export functionality for responses
- Email notifications for new responses
- Advanced analytics with machine learning
- Mobile app integration
- Multi-language support

## Support

For issues or questions, please check the troubleshooting section or create an issue in the repository.