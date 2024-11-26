from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class StaffManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Staff(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = StaffManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

class MaintenanceTicket(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Closed', 'Closed'),
    ]
    
    bathroom_number = models.CharField(max_length=50)
    email = models.EmailField()
    description = models.TextField()
    date_submitted = models.DateTimeField(auto_now_add=True)
    date_closed = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    ticket_number = models.CharField(max_length=10, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            last_ticket = MaintenanceTicket.objects.order_by('-id').first()
            if last_ticket:
                last_id = last_ticket.id
            else:
                last_id = 0
            self.ticket_number = f"{(last_id + 1):03d}"
        
        # Set date_closed when status changes to Closed
        if self.status == 'Closed' and not self.date_closed:
            from django.utils import timezone
            self.date_closed = timezone.now()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.bathroom_number}"
    
class Building(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    building_id = models.CharField(max_length=50, unique=True)
    number_of_floors = models.IntegerField()
    number_of_bathrooms = models.IntegerField()
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Bathroom(models.Model):
    name = models.CharField(max_length=100)
    bathroom_number = models.CharField(max_length=50)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    floor = models.IntegerField()
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.building.name}"

