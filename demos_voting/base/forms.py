from __future__ import absolute_import, division, print_function, unicode_literals

import pytz

from allauth.account.adapter import get_adapter
from allauth.account.forms import AddEmailForm, ResetPasswordForm, ResetPasswordKeyForm, SetPasswordForm, SignupForm

from django import forms
from django.conf import settings
from django.utils import timezone, translation
from django.utils.translation import ugettext_lazy as _


# Language and timezone form ##################################################

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

class AddEmailForm(AddEmailForm):
    def clean(self):
        cleaned_data = super(AddEmailForm, self).clean()
        if not get_adapter().is_open_for_signup(request=None):
            self.add_error(None, forms.ValidationError(_("Adding new email addresses is not allowed.")))
        return cleaned_data


class ResetPasswordForm(ResetPasswordForm):
    def clean(self):
        cleaned_data = super(ResetPasswordForm, self).clean()
        users = getattr(self, 'users', [])
        if users:
            assert len(users) == 1
            if not users[0].has_usable_password() and not get_adapter().is_open_for_signup(request=None):
                self.add_error(None, forms.ValidationError(_("Password reset is not allowed.")))
        return cleaned_data


class ResetPasswordKeyForm(ResetPasswordKeyForm):
    def clean(self):
        cleaned_data = super(ResetPasswordKeyForm, self).clean()
        if not self.user.has_usable_password() and not get_adapter().is_open_for_signup(request=None):
            self.add_error(None, forms.ValidationError(_("Password reset is not allowed.")))
        return cleaned_data


class SetPasswordForm(SetPasswordForm):
    def clean(self):
        cleaned_data = super(SetPasswordForm, self).clean()
        if not get_adapter().is_open_for_signup(request=None):
            self.add_error(None, forms.ValidationError(_("Setting a password is not allowed.")))
        return cleaned_data


class SignupForm(SignupForm):
    def clean(self):
        cleaned_data = super(SignupForm, self).clean()
        if not get_adapter().is_open_for_signup(request=None):
            self.add_error(None, forms.ValidationError(_("User registration is not allowed.")))
        return cleaned_data
