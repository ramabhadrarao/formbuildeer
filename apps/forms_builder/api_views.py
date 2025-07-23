# apps/forms_builder/api_views.py
from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import FormTemplate, FormField, FormSubmission, FormFile
from .serializers import (
    FormTemplateSerializer, FormFieldSerializer, 
    FormSubmissionSerializer, FormSubmitSerializer
)
from apps.workflow.utils import trigger_workflow


class FormListAPI(generics.ListCreateAPIView):
    """List and create forms"""
    serializer_class = FormTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = FormTemplate.objects.filter(is_active=True)
        
        # Filter by search term
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Filter by category
        category = self.request.query_params.get('category', '')
        if category and category != 'all':
            queryset = queryset.filter(category=category)
        
        # Sorting
        sort = self.request.query_params.get('sort', '-updated_at')
        if sort == 'submissions_count':
            queryset = queryset.annotate(
                submissions_count=Count('submissions')
            ).order_by('-submissions_count')
        else:
            queryset = queryset.order_by(sort)
        
        # Add submissions count
        queryset = queryset.annotate(
            submissions_count=Count('submissions')
        )
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class FormDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a form"""
    serializer_class = FormTemplateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return FormTemplate.objects.filter(is_active=True)


class FormSubmitAPI(APIView):
    """Submit a form"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, form_id):
        form_template = get_object_or_404(FormTemplate, id=form_id, is_active=True)
        
        # Check permissions
        if not request.user.has_perm('view_formtemplate', form_template):
            return Response(
                {'error': 'You do not have permission to submit this form'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = FormSubmitSerializer(
            data=request.data,
            context={'form': form_template, 'request': request}
        )
        
        if serializer.is_valid():
            submission = serializer.save()
            
            # Handle file uploads
            for field_name, file in request.FILES.items():
                FormFile.objects.create(
                    submission=submission,
                    field_name=field_name,
                    file=file
                )
            
            # Trigger workflow
            workflow_instance = trigger_workflow(submission)
            
            return Response({
                'success': True,
                'submission_id': str(submission.id),
                'message': 'Form submitted successfully'
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class SubmissionDetailAPI(generics.RetrieveAPIView):
    """Get submission details"""
    serializer_class = FormSubmissionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return FormSubmission.objects.filter(
            Q(submitted_by=self.request.user) |
            Q(assigned_to=self.request.user)
        ).distinct()


class DashboardStatsAPI(APIView):
    """Get dashboard statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        now = timezone.now()
        
        # Calculate date ranges
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Get stats
        total_forms = FormTemplate.objects.filter(is_active=True).count()
        total_submissions = FormSubmission.objects.filter(submitted_by=user).count()
        pending_reviews = FormSubmission.objects.filter(
            assigned_to=user,
            status='pending'
        ).count()
        completed_today = FormSubmission.objects.filter(
            submitted_by=user,
            status='completed',
            submitted_at__gte=today_start
        ).count()
        
        # Calculate changes
        forms_last_week = FormTemplate.objects.filter(
            created_at__gte=week_ago
        ).count()
        submissions_last_week = FormSubmission.objects.filter(
            submitted_by=user,
            submitted_at__gte=week_ago
        ).count()
        
        # Popular forms
        popular_forms = FormTemplate.objects.filter(is_active=True).annotate(
            submissions_count=Count('submissions')
        ).order_by('-submissions_count')[:3]
        
        stats = {
            'userName': user.get_full_name() or user.username,
            'totalForms': total_forms,
            'totalSubmissions': total_submissions,
            'pendingReviews': pending_reviews,
            'completedToday': completed_today,
            'formsChange': forms_last_week,
            'submissionsChange': submissions_last_week,
            'popularForms': FormTemplateSerializer(popular_forms, many=True).data
        }
        
        return Response(stats)


class RecentActivityAPI(APIView):
    """Get recent activity"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get recent submissions
        recent_submissions = FormSubmission.objects.filter(
            Q(submitted_by=user) | Q(assigned_to=user)
        ).select_related('form', 'submitted_by').order_by('-submitted_at')[:10]
        
        activities = []
        for submission in recent_submissions:
            activities.append({
                'id': str(submission.id),
                'type': 'submission',
                'title': f"{submission.submitted_by.get_full_name()} submitted {submission.form.name}",
                'description': f"Status: {submission.status}",
                'timestamp': submission.submitted_at,
                'icon': 'document',
                'link': f"/submissions/{submission.id}"
            })
        
        return Response(activities)


class ChartDataAPI(APIView):
    """Get chart data for dashboard"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        period = request.query_params.get('period', '30d')
        user = request.user
        now = timezone.now()
        
        # Determine date range
        if period == '7d':
            start_date = now - timedelta(days=7)
            date_format = '%a'
        elif period == '90d':
            start_date = now - timedelta(days=90)
            date_format = '%b %d'
        else:  # 30d default
            start_date = now - timedelta(days=30)
            date_format = '%b %d'
        
        # Get submissions data
        submissions = FormSubmission.objects.filter(
            submitted_by=user,
            submitted_at__gte=start_date
        ).extra(
            select={'day': 'date(submitted_at)'}
        ).values('day').annotate(count=Count('id')).order_by('day')
        
        # Format data for chart
        chart_data = []
        current_date = start_date.date()
        end_date = now.date()
        
        submission_dict = {item['day']: item['count'] for item in submissions}
        
        while current_date <= end_date:
            chart_data.append({
                'date': current_date.strftime(date_format),
                'submissions': submission_dict.get(current_date, 0)
            })
            current_date += timedelta(days=1)
        
        return Response(chart_data)


class LookupAPI(APIView):
    """Lookup data for lookup fields"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, model_name):
        query = request.query_params.get('q', '')
        
        if len(query) < 2:
            return Response({'results': []})
        
        # Define model mappings
        from apps.users.models import User, Department, Project
        
        model_map = {
            'user': User,
            'department': Department,
            'project': Project,
        }
        
        model = model_map.get(model_name)
        if not model:
            return Response({'results': []}, status=status.HTTP_404_NOT_FOUND)
        
        # Perform search
        results = []
        if model_name == 'user':
            users = User.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(username__icontains=query) |
                Q(email__icontains=query)
            )[:20]
            
            results = [
                {
                    'id': str(user.id),
                    'label': user.get_full_name() or user.username,
                    'value': user.username,
                    'email': user.email
                }
                for user in users
            ]
        else:
            # Generic search for other models
            objects = model.objects.filter(name__icontains=query)[:20]
            results = [
                {
                    'id': str(obj.id),
                    'label': str(obj),
                    'value': getattr(obj, 'name', str(obj))
                }
                for obj in objects
            ]
        
        return Response({'results': results})