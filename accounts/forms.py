from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser, StudentProfile


class LoginForm(AuthenticationForm):
    """
    AuthenticationForm already handles:
    - username/password field definitions
    - checking credentials against the database
    - the "please enter correct username/password" error message
    - rate limiting and security

    We subclass it ONLY to restyle the HTML widgets with our CSS class.
    We get all the validation logic for free.
    """

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your username',
            'class': 'form-input',
            # 'class' maps to the HTML class attribute: <input class="form-input">
            # Our CSS file has styles for `.form-input`.
            'autofocus': True,
            # The browser puts the cursor here automatically. Small UX detail.
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'form-input',
            # PasswordInput renders as <input type="password"> — browser hides the text.
        })
    )


class StudentRegistrationForm(forms.ModelForm):
    """
    ModelForm reads the model definition and auto-generates fields.
    We list exactly which fields we want in `Meta.fields`.
    Password is handled separately because we must hash it before saving.
    Storing plain-text passwords is a serious security vulnerability.
    """

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password'
        })
    )
    password_confirm = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Repeat your password'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email']
        # We deliberately exclude `role` — it gets set to 'student' in the view.
        # Users should never be able to choose their own role from a form.
        widgets = {
            'username':   forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Choose a username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First name'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last name'}),
            'email':      forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email address'}),
        }

    def clean(self):
        """
        clean() is called after all individual fields pass their own validation.
        This is where you put cross-field validation — logic that needs
        to look at multiple fields at once.
        Raising ValidationError here automatically adds the error to the form
        and prevents saving.
        """
        cleaned_data = super().clean()
        # super().clean() runs the parent class validation first.
        # `cleaned_data` is a dict of validated field values.

        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data


class StudentProfileForm(forms.ModelForm):
    """
    Filled in on the same registration page as StudentRegistrationForm.
    Two forms, one submit button — both must be valid before either saves.
    """

    class Meta:
        model = StudentProfile
        fields = ['roll_number', 'semester', 'branch']
        widgets = {
            'roll_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. CS2022001'
            }),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            # Select renders as <select> — Django auto-populates the <option>
            # tags from the `choices` we defined in the model.
            'branch': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Computer Science'
            }),
        }