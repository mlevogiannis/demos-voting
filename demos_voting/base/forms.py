from __future__ import absolute_import, division, print_function, unicode_literals

import pytz

from allauth.account import app_settings as account_settings, forms as account_forms
from allauth.socialaccount import forms as socialaccount_forms

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone, translation
from django.utils.translation import ugettext_lazy as _


class UserForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name']


class SetLanguageAndTimezoneForm(forms.Form):
    prefix = 'set-language-and-timezone'

    language = forms.ChoiceField(
        label=_("Language"),
        required=False,
        choices=settings.LANGUAGES,
        initial=translation.get_language,
    )
    timezone = forms.ChoiceField(
        label=_("Time zone"),
        required=False,
        choices=[(timezone_name, timezone_name) for timezone_name in pytz.common_timezones],
        initial=timezone.get_current_timezone_name,
    )

    def clean_language(self):
        # Defaults to the initial value if a value is not provided.
        return self.cleaned_data['language'] or self.get_initial_for_field(self.fields['language'], 'language')

    def clean_timezone(self):
        # Defaults to the initial value if a value is not provided.
        return self.cleaned_data['timezone'] or self.get_initial_for_field(self.fields['timezone'], 'timezone')


# Allauth forms ###############################################################

class RemoveWidgetPlaceholderMixin(object):
    def __init__(self, *args, **kwargs):
        super(RemoveWidgetPlaceholderMixin, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.pop('placeholder', None)


class SignupMixin(object):
    def __init__(self, *args, **kwargs):
        super(SignupMixin, self).__init__(*args, **kwargs)
        email_field = self.fields['email']
        email_field.label = _("Email address") if email_field.required else _("Email address (optional)")
        email2_field = self.fields.get('email2')
        if email2_field:
            email2_field.label = _("Email address (again)")


class AccountAddEmailForm(RemoveWidgetPlaceholderMixin, account_forms.AddEmailForm):
    def __init__(self, *args, **kwargs):
        super(AccountAddEmailForm, self).__init__(*args, **kwargs)
        self.fields['email'].label = _("Email address")


class AccountChangePasswordForm(RemoveWidgetPlaceholderMixin, account_forms.ChangePasswordForm):
    pass


class AccountLoginForm(RemoveWidgetPlaceholderMixin, account_forms.LoginForm):
    def __init__(self, *args, **kwargs):
        super(AccountLoginForm, self).__init__(*args, **kwargs)
        login_field = self.fields['login']
        if account_settings.AUTHENTICATION_METHOD == "email":
            login_field.label = _("Email address")
        elif account_settings.AUTHENTICATION_METHOD == "username_email":
            login_field.label = _("Username or email address")


class AccountResetPasswordForm(RemoveWidgetPlaceholderMixin, account_forms.ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(AccountResetPasswordForm, self).__init__(*args, **kwargs)
        self.fields['email'].label = _("Email address")


class AccountResetPasswordKeyForm(RemoveWidgetPlaceholderMixin, account_forms.ResetPasswordKeyForm):
    pass


class AccountSetPasswordForm(RemoveWidgetPlaceholderMixin, account_forms.SetPasswordForm):
    pass


class AccountSignupForm(SignupMixin, RemoveWidgetPlaceholderMixin, account_forms.SignupForm):
    pass


class SocialAccountDisconnectForm(RemoveWidgetPlaceholderMixin, socialaccount_forms.DisconnectForm):
    pass


class SocialAccountSignupForm(SignupMixin, RemoveWidgetPlaceholderMixin, socialaccount_forms.SignupForm):
    pass
