from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from app.models import Profile, Review, Provider, Category


from django.db import transaction

class CustomUserCreationForm(UserCreationForm):
    is_provider = forms.BooleanField(required=False, label="Are you a provider?")
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email já está em uso.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()

            profile = Profile.objects.create(user=user)

            if self.cleaned_data['is_provider']:
                Provider.objects.create(profile=profile)
        return user

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control input w-full',
            'placeholder': 'Enter your username'
        }),
        label="Username"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control input w-full',
            'placeholder': 'Enter your password'
        }),
        label="Password"
    )

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'phone', 'location']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': 'image/*',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter your phone number',
            }),
            'location': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter your location',
            }),
        }

class ProviderForm(forms.ModelForm):
    avatar = forms.ImageField(required=False, widget=forms.FileInput(attrs={
        'class': 'file-input file-input-bordered w-full',
        'accept': 'image/*',
    }))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'input input-bordered w-full',
        'placeholder': 'Enter your phone number',
    }))
    location = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'input input-bordered w-full',
        'placeholder': 'Enter your location',
    }))

    class Meta:
        model = Provider
        fields = ['about', 'contact_email', 'linkedin', 'twitter', 'facebook']
        widgets = {
            'about': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'placeholder': 'Tell us about yourself',
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter your email',
            }),
            'linkedin': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://linkedin.com/in/username',
            }),
            'twitter': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://twitter.com/username',
            }),
            'facebook': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://facebook.com/username',
            }),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')  # Get the Provider instance
        if instance and instance.profile:  # Check if the instance has an associated Profile
            initial = kwargs.setdefault('initial', {})
            initial['avatar'] = instance.profile.avatar
            initial['phone'] = instance.profile.phone
            initial['location'] = instance.profile.location
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        provider = super().save(commit=False)  # Save Provider fields
        profile = provider.profile  # Access the related Profile instance

        # Update Profile fields
        profile.avatar = self.cleaned_data.get('avatar')
        profile.phone = self.cleaned_data.get('phone')
        profile.location = self.cleaned_data.get('location')

        if commit:
            profile.save()  # Save Profile
            provider.save()  # Save Provider
        return provider

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.HiddenInput(),  # Hide the default rating input
            'comment': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 5, 'placeholder': 'Write your review here'}),
        }

class AddBalanceForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Amount",
        widget=forms.NumberInput(attrs={
            'id': 'balance_amount',
            'class': 'input input-bordered w-full',  # Add your desired classes
            'step': '0.01',
            'min': '0',
            'required': 'required',  # Ensure the field is marked as required
            'placeholder': 'Enter the amount to add'  # Optional placeholder
        })
    )

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Enter category name'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3, 'placeholder': 'Enter category description'}),
        }