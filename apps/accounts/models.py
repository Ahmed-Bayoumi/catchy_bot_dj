# Models:
# 1. User - Custom user model (replaces Django's default)
# 2. UserProfile - Extended user information


from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _



# USER MANAGER (handles user creation)
class UserManager(BaseUserManager):
    """
    Custom user manager for User model

    Provides methods to:
    - Create regular users
    - Create superusers (admins)
    - Handle email-based authentication
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user

        Args:
            email (str): User's email address (required)
            password (str): User's password (required)
            **extra_fields: Additional fields (first_name, last_name, etc.)

        Returns:
            User: The created user object

        Raises:
            ValueError: If email is not provided

        Example:
            user = User.objects.create_user(
                email='agent@clinic.com',
                password='securepass123',
                first_name='Ahmed',
                last_name='Ali',
                role='agent'
            )
        """
        if not email:
            raise ValueError(_('Users must have an email address'))

        # Normalize email (convert domain to lowercase)
        email = self.normalize_email(email)

        # Set default values for required fields
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        # Create user instance
        user = self.model(email=email, **extra_fields)

        # Set password (hashed)
        user.set_password(password)

        # Save to database
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser (admin)

        Superusers have all permissions and can access admin panel

        Args:
            email (str): Admin email
            password (str): Admin password
            **extra_fields: Additional fields
        """
        # Set required superuser flags
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')

        # Validate flags
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True'))

        # Create user
        return self.create_user(email, password, **extra_fields)



# USER MODEL
class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for Catchy Bot

    Features:
    - Email-based authentication (no username)
    - Multi-tenancy support (company field)
    - Role-based access (admin, agent)
    - Performance tracking (leads assigned, converted, won)
    - Activity tracking (login count, last login, IP)
    """

    # Email as primary identifier (instead of username)
    email = models.EmailField(_('email address'),unique=True,max_length=255,db_index=True,help_text=_('Required. Used for login.'))
    first_name = models.CharField(_('first name'),max_length=50,blank=True,help_text=_('User\'s first name (e.g., Ahmed)'))
    last_name = models.CharField(_('last name'),max_length=50,blank=True,help_text=_('User\'s last name (e.g., Ali)'))

    # Phone validator (accepts: +201234567890, 01234567890, etc.)
    phone_validator = RegexValidator(regex=r'^\+?1?\d{9,15}$',message=_('Phone number must be entered in the format: +999999999. Up to 15 digits allowed.'))
    phone = models.CharField(_('phone number'),validators=[phone_validator],max_length=17,blank=True,null=True,help_text=_('Contact phone number (e.g., +201234567890)'))

    # COMPANY & ROLE (Multi-tenancy)
    company = models.ForeignKey('core.Company',on_delete=models.CASCADE,related_name='users',
              null=True,blank=True,verbose_name=_('company'),help_text=_('The clinic/company this user belongs to'))

    role = models.CharField(_('role'),max_length=20,choices=[('admin', _('Administrator')), ('agent', _('Agent')),],
                            default='agent',db_index=True,help_text=_('User role: admin (full access) or agent (limited access)'))

    avatar = models.ImageField(_('profile picture'),upload_to='avatars/%Y/%m/', blank=True,null=True,help_text=_('Profile picture (recommended: 300x300px, max 2MB)'))
    job_title = models.CharField(_('job title'),max_length=100,blank=True,help_text=_('e.g., Sales Manager, Customer Service Agent'))
    department = models.CharField(_('department'),max_length=100,blank=True,help_text=_('e.g., Sales, Customer Support, Administration'))

    total_leads_assigned = models.PositiveIntegerField(_('total leads assigned'), default=0,help_text=_('Total number of leads assigned to this user'))
    total_leads_converted = models.PositiveIntegerField(_('total leads converted'), default=0,help_text=_('Number of leads converted to patients'))
    total_leads_won = models.PositiveIntegerField(_('total leads won'), default=0,help_text=_('Number of leads that resulted in successful sales'))
    login_count = models.PositiveIntegerField(_('login count'), default=0,help_text=_('Number of times user has logged in'))
    last_login_ip = models.GenericIPAddressField(_('last login IP'), blank=True, null=True,help_text=_('IP address of last login'))
    is_active = models.BooleanField(_('active'), default=True, help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))
    is_staff = models.BooleanField(_('staff status'), default=False,help_text=_('Designates whether the user can log into admin site.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now,help_text=_('Date when user account was created'))
    updated_at = models.DateTimeField(_('updated at'), auto_now=True, help_text=_('Last time user profile was updated'))

    # MANAGER & SETTINGS
    objects = UserManager()

    # Use email as the unique identifier for authentication
    USERNAME_FIELD = 'email'

    # Fields required when creating superuser (in addition to email and password)
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # META OPTIONS
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']  # Newest first
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['company', 'role']),
            models.Index(fields=['is_active']),
        ]

    # STRING REPRESENTATION
    def __str__(self):
        """
        String representation of user

        Returns:
            str: User's full name and email

        Example:
            "Ahmed Ali (ahmed@clinic.com)"
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.email})"
        return self.email

    # HELPER METHODS
    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email

    def get_short_name(self):

        return self.first_name if self.first_name else self.email

    def get_initials(self):
        """
        Get user's initials
        Returns:
            str: First letter of first name + first letter of last name
        """
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        return self.email[0].upper()

    # ROLE CHECKS
    def is_admin(self):

        return self.role == 'admin' or self.is_superuser

    def is_agent(self):

        return self.role == 'agent'

    # PERFORMANCE CALCULATIONS
    def get_conversion_rate(self):
        """
        Calculate lead conversion rate

        Formula: (converted leads / assigned leads) * 100

        Returns:
            float: Conversion rate percentage (0-100)
        """
        if self.total_leads_assigned == 0:
            return 0.0
        return (self.total_leads_converted / self.total_leads_assigned) * 100

    def get_win_rate(self):
        """
        Calculate lead win rate

        Formula: (won leads / assigned leads) * 100

        Returns:
            float: Win rate percentage (0-100)
        """
        if self.total_leads_assigned == 0:
            return 0.0
        return (self.total_leads_won / self.total_leads_assigned) * 100

    def get_performance_score(self):
        """
        Calculate overall performance score

        Formula: (conversion_rate * 0.6) + (win_rate * 0.4)
        Weights: Conversion is more important (60%) than win (40%)

        Returns:
            float: Performance score (0-100)

        Example:
            >>> user.get_conversion_rate()  # 30%
            >>> user.get_win_rate()  # 25%
            >>> user.get_performance_score()
            28.0  # (30 * 0.6) + (25 * 0.4)
        """
        conversion_rate = self.get_conversion_rate()
        win_rate = self.get_win_rate()
        return (conversion_rate * 0.6) + (win_rate * 0.4)

    # ACTIVITY TRACKING
    def increment_login_count(self, ip_address=None):
        """
        Increment login count and update last login IP

        Called when user logs in successfully

        Args:
            ip_address (str, optional): User's IP address

        Example:
            user.increment_login_count(ip_address='192.168.1.1')
        """
        self.login_count += 1
        if ip_address:
            self.last_login_ip = ip_address
        self.save(update_fields=['login_count', 'last_login_ip'])

    def increment_leads_assigned(self, count=1):
        """
        Increment total leads assigned

        Args:
            count (int): Number to increment by (default: 1)
        """
        self.total_leads_assigned += count
        self.save(update_fields=['total_leads_assigned'])

    def increment_leads_converted(self, count=1):
        """
        Increment total leads converted

        Args:
            count (int): Number to increment by (default: 1)
        """
        self.total_leads_converted += count
        self.save(update_fields=['total_leads_converted'])

    def increment_leads_won(self, count=1):
        """
        Increment total leads won

        Args:
            count (int): Number to increment by (default: 1)
        """
        self.total_leads_won += count
        self.save(update_fields=['total_leads_won'])



# USER PROFILE MODEL (Extended Information)

class UserProfile(models.Model):
    """
    Extended user profile information

    This model stores additional user information that doesn't belong in User model
    Automatically created when User is created (via signals)

    Fields:
    - bio: User biography/description
    - date_of_birth: Birthday
    - address: Physical address
    - city: City
    - country: Country
    - preferences: JSON field for user preferences
    - notification_settings: Email/SMS notification preferences

    Why separate model?
    1. Keeps User model clean and focused
    2. One-to-One relationship (each user has one profile)
    3. Can be extended easily
    4. Better database performance
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name=_('user'),help_text=_('The user this profile belongs to'))
    bio = models.TextField(_('biography'), max_length=500, blank=True, help_text=_('Short bio or description (max 500 characters)'))
    date_of_birth = models.DateField(_('date of birth'), blank=True, null=True, help_text=_("User's birthday"))
    address = models.CharField(_('address'), max_length=255, blank=True, help_text=_('Street address'))
    city = models.CharField(_('city'), max_length=100, blank=True, help_text=_('City name'))
    country = models.CharField(_('country'), max_length=100, blank=True, default='Egypt', help_text=_('Country name'))
    email_notifications = models.BooleanField(_('email notifications'), default=True, help_text=_('Receive notifications via email'))
    sms_notifications = models.BooleanField(_('SMS notifications'), default=False,help_text=_('Receive notifications via SMS'))
    theme = models.CharField(_('theme'), max_length=20, choices=[('light', _('Light')), ('dark', _('Dark')), ('auto', _('Auto'))], default='light',
                             help_text=_('UI theme preference'))
    language = models.CharField(_('language'), max_length=10, choices=[('ar', _('Arabic')), ('en', _('English'))],
                                default='en', help_text=_('Preferred language'))
    linkedin_url = models.URLField(_('LinkedIn profile'), max_length=255, blank=True,help_text=_('LinkedIn profile URL'))
    twitter_url = models.URLField(_('Twitter profile'), max_length=255, blank=True, help_text=_('Twitter profile URL'))
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)


    class Meta:
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')

    # STRING REPRESENTATION

    def __str__(self):
        return f"Profile for: {self.user.get_full_name()}"

    # HELPER METHODS
    def get_age(self):
        if not self.date_of_birth:
            return None

        today = timezone.now().date()
        age = today.year - self.date_of_birth.year

        # Adjust if birthday hasn't occurred this year
        if today.month < self.date_of_birth.month or \
                (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
            age -= 1

        return age

    def is_complete(self):
        """
        Check if profile is complete

        A complete profile has:
        - Bio filled
        - Date of birth set
        - Address filled
        - City filled
        """
        return all([
            self.bio,
            self.date_of_birth,
            self.address,
            self.city,
        ])

    def get_completion_percentage(self):
        """
        Calculate profile completion percentage

        Returns:
            int: Completion percentage (0-100)
        """
        fields = [
            self.bio,
            self.date_of_birth,
            self.address,
            self.city,
            self.user.phone,
            self.user.avatar,
        ]

        filled = sum(1 for field in fields if field)
        return int((filled / len(fields)) * 100)

# ==============================================================================
# NOTES & BEST PRACTICES
# ==============================================================================
#
# 1. NEVER modify User model after migrations!
#    - Add new fields to UserProfile instead
#    - Or create new related models
#
# 2. Always use get_user_model() instead of importing User directly:
#    from django.contrib.auth import get_user_model
#    User = get_user_model()
#
# 3. Performance optimization:
#    - Use select_related() when querying user with company
#    - Use prefetch_related() for reverse relationships
#    Example:
#    users = User.objects.select_related('company', 'profile').all()
#
# 4. Security:
#    - Never store plain passwords (use set_password())
#    - Always validate email uniqueness
#    - Check is_active before allowing login
#
# 5. Testing:
#    - Create test users with create_user()
#    - Test all helper methods
#    - Test role checks
#    - Test performance calculations
#
# ==============================================================================