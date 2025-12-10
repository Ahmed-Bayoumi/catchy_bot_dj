
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, Field, HTML
from crispy_forms.bootstrap import FormActions

from .models import UserProfile

User = get_user_model()


# LOGIN FORM
class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_('Email Address'),
        max_length=255,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('example@clinic.com'),
            'autofocus': True,
        })
    )

    password = forms.CharField(
        label=_('Password'),
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password'),
        })
    )

    remember = forms.BooleanField(
        label=_('Remember me'),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'

        # Form layout
        self.helper.layout = Layout(
            Field('email', css_class='mb-3'),
            Field('password', css_class='mb-3'),
            Field('remember', css_class='mb-3'),
            FormActions(
                Submit('submit', _('Login'), css_class='btn btn-primary btn-block w-100')
            )
        )

    def clean_email(self):

        email = self.cleaned_data.get('email', '')
        return email.lower().strip()


# USER EDIT FORM
class UserEditForm(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'phone',
            'avatar',
            'job_title',
            'department',
            'role',
            'is_active',
        ]

        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('First name'),
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Last name'),
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('+201234567890'),
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'job_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Sales Manager'),
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Sales Department'),
            }),
            'role': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

        labels = {
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'phone': _('Phone Number'),
            'avatar': _('Profile Picture'),
            'job_title': _('Job Title'),
            'department': _('Department'),
            'role': _('Role'),
            'is_active': _('Active'),
        }

        help_texts = {
            'avatar': _('Recommended: 300x300px, max 2MB (JPG, PNG)'),
            'phone': _('Format: +201234567890'),
            'role': _('Admin: Full access | Agent: Limited access'),
        }

    def __init__(self, *args, **kwargs):

        # Extract custom parameter
        can_edit_all_fields = kwargs.pop('can_edit_all_fields', False)

        super().__init__(*args, **kwargs)

        # Remove admin-only fields if user is not admin
        if not can_edit_all_fields:
            self.fields.pop('role', None)
            self.fields.pop('is_active', None)

        # Crispy forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'  # For file upload

        # Dynamic layout based on permissions
        if can_edit_all_fields:
            layout = Layout(
                Fieldset(
                    _('Personal Information'),
                    Div(
                        Div('first_name', css_class='col-md-6'),
                        Div('last_name', css_class='col-md-6'),
                        css_class='row'
                    ),
                    Div(
                        Div('phone', css_class='col-md-6'),
                        Div('avatar', css_class='col-md-6'),
                        css_class='row'
                    ),
                ),
                Fieldset(
                    _('Job Information'),
                    Div(
                        Div('job_title', css_class='col-md-6'),
                        Div('department', css_class='col-md-6'),
                        css_class='row'
                    ),
                ),
                Fieldset(
                    _('Role & Status'),
                    Div(
                        Div('role', css_class='col-md-6'),
                        Div('is_active', css_class='col-md-6'),
                        css_class='row'
                    ),
                ),
                FormActions(
                    Submit('submit', _('Update'), css_class='btn btn-primary'),
                    HTML('<a href="{{ request.META.HTTP_REFERER }}" class="btn btn-secondary">Cancel</a>'),
                )
            )
        else:
            layout = Layout(
                Fieldset(
                    _('Personal Information'),
                    Div(
                        Div('first_name', css_class='col-md-6'),
                        Div('last_name', css_class='col-md-6'),
                        css_class='row'
                    ),
                    Div(
                        Div('phone', css_class='col-md-6'),
                        Div('avatar', css_class='col-md-6'),
                        css_class='row'
                    ),
                ),
                Fieldset(
                    _('Job Information'),
                    Div(
                        Div('job_title', css_class='col-md-6'),
                        Div('department', css_class='col-md-6'),
                        css_class='row'
                    ),
                ),
                FormActions(
                    Submit('submit', _('Update'), css_class='btn btn-primary'),
                    HTML('<a href="{% url \'accounts:profile\' %}" class="btn btn-secondary">Cancel</a>'),
                )
            )

        self.helper.layout = layout

    def clean_avatar(self):

        avatar = self.cleaned_data.get('avatar')

        if avatar:
            # Check file size (2MB = 2 * 1024 * 1024 bytes)
            max_size = 2 * 1024 * 1024
            if avatar.size > max_size:
                raise ValidationError(
                    _('Avatar file size must be less than 2MB.')
                )

            # Check file type
            if not avatar.content_type.startswith('image/'):
                raise ValidationError(
                    _('Avatar must be an image file (JPG, PNG, GIF).')
                )

        return avatar



# USER CREATE FORM
class UserCreateForm(UserCreationForm):

    email = forms.EmailField(
        label=_('Email Address'),
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('user@clinic.com'),
        })
    )

    first_name = forms.CharField(
        label=_('First Name'),
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ahmed'),
        })
    )

    last_name = forms.CharField(
        label=_('Last Name'),
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ali'),
        })
    )

    phone = forms.CharField(
        label=_('Phone Number'),
        max_length=17,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('+201234567890'),
        })
    )

    role = forms.ChoiceField(
        label=_('Role'),
        choices=[('admin', _('Administrator')), ('agent', _('Agent')),],
        initial='agent',
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'role', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Update password field widgets
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter password'),
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm password'),
        })

        # Crispy forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Fieldset(
                _('Login Information'),
                'email',
                Div(
                    Div('password1', css_class='col-md-6'),
                    Div('password2', css_class='col-md-6'),
                    css_class='row'
                ),
            ),
            Fieldset(
                _('Personal Information'),
                Div(
                    Div('first_name', css_class='col-md-6'),
                    Div('last_name', css_class='col-md-6'),
                    css_class='row'
                ),
                'phone',
            ),
            Fieldset(
                _('Role'),
                'role',
            ),
            FormActions(
                Submit('submit', _('Create User'), css_class='btn btn-primary'),
                HTML('<a href="{% url \'accounts:user_list\' %}" class="btn btn-secondary">Cancel</a>'),
            )
        )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                _('A user with this email already exists.')
            )

        return email


# USER PROFILE FORM
class UserProfileForm(forms.ModelForm):

    class Meta:
        model = UserProfile
        fields = [
            'bio',
            'date_of_birth',
            'address',
            'city',
            'country',
            'email_notifications',
            'sms_notifications',
            'theme',
            # 'language',
            # 'linkedin_url',
            # 'twitter_url',
        ]

        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Tell us about yourself...'),
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Street address'),
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Cairo'),
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Egypt'),
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'sms_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'theme': forms.Select(attrs={
                'class': 'form-select',
            }),
            # 'language': forms.Select(attrs={
            #     'class': 'form-select',
            # }),
            # 'linkedin_url': forms.URLInput(attrs={
            #     'class': 'form-control',
            #     'placeholder': _('https://linkedin.com/in/username'),
            # }),
            # 'twitter_url': forms.URLInput(attrs={
            #     'class': 'form-control',
            #     'placeholder': _('https://twitter.com/username'),
            # }),
        }

        labels = {
            'bio': _('Biography'),
            'date_of_birth': _('Date of Birth'),
            'address': _('Address'),
            'city': _('City'),
            'country': _('Country'),
            'email_notifications': _('Email Notifications'),
            'sms_notifications': _('SMS Notifications'),
            'theme': _('Theme'),
            # 'language': _('Language'),
            # 'linkedin_url': _('LinkedIn Profile'),
            # 'twitter_url': _('Twitter Profile'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Crispy forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Fieldset(
                _('Personal Information'),
                'bio',
                Div(
                    Div('date_of_birth', css_class='col-md-4'),
                    Div('city', css_class='col-md-4'),
                    Div('country', css_class='col-md-4'),
                    css_class='row'
                ),
                'address',
            ),
            Fieldset(
                _('Notifications'),
                Div(
                    Div('email_notifications', css_class='col-md-6'),
                    Div('sms_notifications', css_class='col-md-6'),
                    css_class='row'
                ),
            ),
            Fieldset(
                _('Preferences'),
                Div(
                    Div('theme', css_class='col-md-6'),
                    # Div('language', css_class='col-md-6'),
                    css_class='row'
                ),
            ),
            # Fieldset(
            #     _('Social Links'),
            #     'linkedin_url',
            #     'twitter_url',
            # ),
        )


# PASSWORD RESET FORMS
class PasswordResetRequestForm(forms.Form):

    email = forms.EmailField(
        label=_('Email Address'),
        max_length=255,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('your-email@clinic.com'),
            'autofocus': True,
        }),
        help_text=_('Enter your email address to receive password reset instructions.')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            'email',
            FormActions(
                Submit('submit', _('Send Reset Link'), css_class='btn btn-primary btn-block w-100')
            )
        )

    def clean_email(self):
        """Clean and normalize email"""
        email = self.cleaned_data.get('email', '').lower().strip()
        return email


class PasswordResetConfirmForm(forms.Form):

    new_password1 = forms.CharField(
        label=_('New Password'),
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter new password'),
            'autofocus': True,
        }),
        help_text=_('Password must be at least 8 characters long.')
    )

    new_password2 = forms.CharField(
        label=_('Confirm Password'),
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm new password'),
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            'new_password1',
            'new_password2',
            FormActions(
                Submit('submit', _('Reset Password'), css_class='btn btn-primary btn-block w-100')
            )
        )

    def clean_new_password1(self):

        password = self.cleaned_data.get('new_password1')

        if len(password) < 8:
            raise ValidationError(
                _('Password must be at least 8 characters long.')
            )

        # Optional: Add more checks
        # if not any(char.isdigit() for char in password):
        #     raise ValidationError(_('Password must contain at least one number.'))

        # if not any(char.isalpha() for char in password):
        #     raise ValidationError(_('Password must contain at least one letter.'))

        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError(
                _('The two password fields must match.')
            )

        return cleaned_data


# FORM VALIDATION HELPERS
def validate_phone_number(value):
    import re

    # Pattern: optional +, then 9-15 digits
    pattern = r'^\+?1?\d{9,15}$'

    if not re.match(pattern, value):
        raise ValidationError(
            _('Invalid phone number format. Use: +201234567890')
        )
