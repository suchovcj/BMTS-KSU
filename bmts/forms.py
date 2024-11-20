from django import forms
from .models import MaintenanceTicket

class StaffLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter password'
    }))

class MaintenanceTicketForm(forms.ModelForm):
    class Meta:
        model = MaintenanceTicket
        fields = ['bathroom_number', 'email', 'description']
        widgets = {
            'bathroom_number': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'required': True
            })
        }