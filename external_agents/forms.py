# external_agents/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import AgentProfile

class AgentRegistrationForm(forms.Form):
    # Разрешаем только ИП и ОсОО
    AGENT_TYPE_CHOICES = (
        ('IP', 'Индивидуальный предприниматель (ИП)'),
        ('COMPANY', 'Юридическое лицо (ОсОО)'),
    )

    agent_code = forms.CharField(
        label="Префикс / Код агента", 
        max_length=30, 
        required=True
    )
    agent_type = forms.ChoiceField(
        label="Тип агента", 
        choices=AGENT_TYPE_CHOICES, 
        initial='IP',
        required=True
    )

    # ФИО и контакты
    first_name = forms.CharField(label="Имя", max_length=150, required=True)
    last_name = forms.CharField(label="Фамилия", max_length=150, required=True)
    middle_name = forms.CharField(label="Отчество", max_length=150, required=False)
    email = forms.EmailField(label="Email (Логин)", required=True)
    phone = forms.CharField(label="Телефон", max_length=30, required=True)
    

    # Реквизиты ИП / ОсОО
    company_name = forms.CharField(label="Название ИП / ОсОО", max_length=255, required=True)
    inn = forms.CharField(label="ИНН (14 цифр)", max_length=14, required=True)
    passport_data = forms.CharField(label="Паспортные данные / Свидетельство", max_length=255, required=False)
    okpo = forms.CharField(label="ОКПО", max_length=20, required=False)
    power_of_attorney = forms.CharField(label="Доверенность", max_length=255, required=False)

    # Банковские реквизиты
    bank_name = forms.CharField(label="Название банка", max_length=255, required=True)
    bik = forms.CharField(label="БИК", max_length=20, required=True)
    account_number = forms.CharField(label="Расчетный счет", max_length=50, required=True)

    # Комиссии
    commission_vzr = forms.DecimalField(label="Комиссия ВЗР (%)", max_digits=5, decimal_places=2, initial=15.00, required=True)
    commission_nomad = forms.DecimalField(label="Комиссия Nomad (%)", max_digits=5, decimal_places=2, initial=20.00, required=True)
    commission_student = forms.DecimalField(label="Комиссия Student (%)", max_digits=5, decimal_places=2, initial=20.00, required=True)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким Email уже существует!")
        return email

    def clean_inn(self):
        """Проверка уникальности ИНН в таблице AgentProfile"""
        inn = self.cleaned_data.get('inn', '').strip()
        
        # Если ИНН заполнен, проверяем на дубликат
        if inn and AgentProfile.objects.filter(inn=inn).exists():
            raise forms.ValidationError(
                "Агент с таким ИНН уже существует в базе данных."
            )
        return inn


# external_agents/forms.py
from django import forms
from django.contrib.auth.models import User, Group
from insurance.models import Branch, Profile
from .models import AgentProfile, AgentCommission

# --- ФОРМА ШТАТНОГО СОТРУДНИКА ---
# external_agents/forms.py
from django import forms
from django.contrib.auth.models import User, Group
from insurance.models import Branch, Profile

class StaffUserForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Имя", 
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Введите имя'})
    )
    last_name = forms.CharField(
        label="Фамилия", 
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Введите фамилию'})
    )
    email = forms.EmailField(
        label="Email (Логин в системе)", 
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'example@gso.kg'})
    )
    branch = forms.ModelChoiceField(
        label="Филиал / Подразделение", 
        queryset=Branch.objects.all(), 
        required=False,
        empty_label="— Головной офис / Не выбран —",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    role = forms.ModelChoiceField(
        label="Роль / Права доступа", 
        queryset=Group.objects.exclude(name='AGENT'), 
        required=True,
        empty_label="Выберите роль",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.BooleanField(
        label="Аккаунт активен (разрешить вход)", 
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        query = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise forms.ValidationError("Пользователь с таким Email уже зарегистрирован в системе.")
        return email


# --- ФОРМА РЕДАКТИРОВАНИЯ ВНЕШНЕГО АГЕНТА ---
class AgentEditForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Имя / Руководитель", 
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    last_name = forms.CharField(
        label="Фамилия", 
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    email = forms.EmailField(
        label="Email (Логин в CRM)", 
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input'})
    )
    
    # Комиссионное вознаграждение (%)
    commission_vzr = forms.DecimalField(
        label="Комиссия ВЗР (%)", 
        max_digits=5, decimal_places=2, min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'})
    )
    commission_nomad = forms.DecimalField(
        label="Комиссия Nomad (%)", 
        max_digits=5, decimal_places=2, min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'})
    )
    commission_student = forms.DecimalField(
        label="Комиссия Student (%)", 
        max_digits=5, decimal_places=2, min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'})
    )

    class Meta:
        model = AgentProfile
        fields = [
            'agent_type', 'phone', 'middle_name', 'company_name', 
            'inn', 'passport_data', 'okpo', 'power_of_attorney', 
            'bank_name', 'bik', 'account_number', 'is_active'
        ]
        widgets = {
            'agent_type': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-input'}),
            'company_name': forms.TextInput(attrs={'class': 'form-input'}),
            'inn': forms.TextInput(attrs={'class': 'form-input'}),
            'passport_data': forms.TextInput(attrs={'class': 'form-input'}),
            'okpo': forms.TextInput(attrs={'class': 'form-input'}),
            'power_of_attorney': forms.TextInput(attrs={'class': 'form-input'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-input'}),
            'bik': forms.TextInput(attrs={'class': 'form-input'}),
            'account_number': forms.TextInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        query = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.user:
            query = query.exclude(pk=self.instance.user.pk)
        if query.exists():
            raise forms.ValidationError("Этот Email уже используется другим пользователем.")
        return email