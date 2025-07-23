# apps/users/management/commands/create_superuser.py
from django.core.management.base import BaseCommand
from apps.users.models import User, Department

class Command(BaseCommand):
    help = 'Create a superuser and sample data'

    def handle(self, *args, **options):
        # Create departments
        if not Department.objects.exists():
            departments = [
                ('IT', 'Information Technology'),
                ('HR', 'Human Resources'),
                ('Finance', 'Finance Department'),
                ('Operations', 'Operations'),
            ]
            
            for name, desc in departments:
                Department.objects.create(name=name, description=desc)
                self.stdout.write(f'Created department: {name}')
        
        # Create superuser
        if not User.objects.filter(is_superuser=True).exists():
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='User',
                role='admin',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write('Created superuser: admin/admin123')
        
        # Create sample users
        if User.objects.count() == 1:  # Only superuser exists
            it_dept = Department.objects.get(name='IT')
            
            users = [
                ('manager', 'manager@example.com', 'Manager', 'User', 'manager'),
                ('user1', 'user1@example.com', 'John', 'Doe', 'user'),
                ('user2', 'user2@example.com', 'Jane', 'Smith', 'user'),
            ]
            
            for username, email, first_name, last_name, role in users:
                User.objects.create_user(
                    username=username,
                    email=email,
                    password='password123',
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    department=it_dept
                )
                self.stdout.write(f'Created user: {username}/password123')
        
        self.stdout.write(self.style.SUCCESS('Setup completed successfully!'))