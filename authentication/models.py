from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator


class UserManager(BaseUserManager):
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
        extra_fields.setdefault('role', 'super_admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('business_owner', 'Business Owner'),
        ('accountant', 'Accountant'),
        ('employee', 'Employee'),
        ('hr_manager', 'HR Manager'),
    ]
    
    PARISH_CHOICES = [
        ('Kingston', 'Kingston'),
        ('St. Andrew', 'St. Andrew'),
        ('St. Thomas', 'St. Thomas'),
        ('Portland', 'Portland'),
        ('St. Mary', 'St. Mary'),
        ('St. Ann', 'St. Ann'),
        ('Trelawny', 'Trelawny'),
        ('St. James', 'St. James'),
        ('Hanover', 'Hanover'),
        ('Westmoreland', 'Westmoreland'),
        ('St. Elizabeth', 'St. Elizabeth'),
        ('Manchester', 'Manchester'),
        ('Clarendon', 'Clarendon'),
        ('St. Catherine', 'St. Catherine'),
    ]

    # Override username to use email
    username = None
    email = models.EmailField(unique=True)
    
    # Personal Information
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")]
    )
    
    # Address Information
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    parish = models.CharField(max_length=20, choices=PARISH_CHOICES, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=100, default='Jamaica')
    
    # Tax Information
    trn = models.CharField(
        max_length=9, 
        blank=True,
        null=True, 
        validators=[RegexValidator(regex=r'^\d{9}$', message="TRN must be exactly 9 digits")]
    )
    nis = models.CharField(
        max_length=9, 
        blank=True,
        null=True, 
        validators=[RegexValidator(regex=r'^\d{9}$', message="NIS must be exactly 9 digits")]
    )
    
    # Verification and Security
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=255, blank=True)
    password_reset_token = models.CharField(max_length=255, blank=True)
    password_reset_expires = models.DateTimeField(null=True, blank=True)
    
    # Timestamp fields (matching database schema)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    last_login_time = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    current_business_id = models.BigIntegerField(null=True, blank=True)
    
    # Set email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = UserManager()
    
    class Meta:
        db_table = 'auth_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['trn']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def has_role(self, role):
        return self.role == role
    
    def is_business_owner(self):
        return self.role == 'business_owner'
    
    def is_super_admin(self):
        return self.role == 'super_admin'
    
