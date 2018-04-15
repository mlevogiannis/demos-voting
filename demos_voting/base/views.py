from __future__ import absolute_import, division, print_function, unicode_literals

from allauth.account import app_settings as account_settings

from django import http
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.utils import translation
from django.utils.functional import cached_property
from django.utils.http import is_safe_url, urlunquote
from django.views import View
from django.views.generic import TemplateView

from rules.contrib.views import PermissionRequiredMixin as BasePermissionRequiredMixin

from demos_voting.base.forms import SetLanguageAndTimezoneForm


# View mixins #################################################################

class PermissionRequiredMixin(BasePermissionRequiredMixin):
    @property
    def raise_exception(self):
        """
        Raise a PermissionDenied exception if the user is authenticated or
        redirect the user to the login page if the user is anonymous. For
        more, see Django's `PermissionRequiredMixin` and `AccessMixin` docs.
        """
        return self.request.user.is_authenticated


class SelectForUpdateMixin(object):
    safe_http_method_names = {'get', 'head', 'options'}

    @cached_property
    def select_for_update(self):
        method_name = self.request.method.lower()
        return (method_name in self.http_method_names and hasattr(self, method_name) and
                method_name not in self.safe_http_method_names)

    def dispatch(self, request, *args, **kwargs):
        if self.select_for_update:
            with transaction.atomic():
                return super(SelectForUpdateMixin, self).dispatch(request, *args, **kwargs)
        else:
            return super(SelectForUpdateMixin, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(SelectForUpdateMixin, self).get_queryset()
        if self.select_for_update:
            queryset = queryset.select_for_update()
        return queryset


class RedirectMixin(object):
    redirect_field_name = 'next'

    def get_redirect_url(self, fallback=False):
        """
        Return the user-originating redirect URL or optionally fall back to the
        URL from the `Referer` header. Return `None` if none of them is safe.
        """
        is_safe_url_kwargs = {
            'allowed_hosts': {self.request.get_host()},
            'require_https': self.request.is_secure(),
        }
        redirect_url = self.request.POST.get(self.redirect_field_name, self.request.GET.get(self.redirect_field_name))
        if not is_safe_url(url=redirect_url, **is_safe_url_kwargs):
            if fallback:
                redirect_url = self.request.META.get('HTTP_REFERER')
                if redirect_url:
                    redirect_url = urlunquote(redirect_url)
                if not is_safe_url(url=redirect_url, **is_safe_url_kwargs):
                    redirect_url = None
            else:
                redirect_url = None
        return redirect_url


# Views #######################################################################

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'account/profile.html'

    def get_context_data(self, **kwargs):
        context = super(ProfileView, self).get_context_data(**kwargs)
        context['username_required'] = account_settings.USERNAME_REQUIRED
        return context


class SetLanguageAndTimezoneView(RedirectMixin, View):
    def post(self, request):
        form = SetLanguageAndTimezoneForm(data=request.POST)
        if form.is_valid():
            language_code = form.cleaned_data['language']
            timezone_name = form.cleaned_data['timezone']
            # Update the user's profile if the user is authenticated.
            user = request.user
            if user.is_authenticated:
                update_fields = []
                profile = user.profile
                if profile.language != language_code:
                    profile.language = language_code
                    update_fields.append('language')
                if profile.timezone != timezone_name:
                    profile.timezone = timezone_name
                    update_fields.append('timezone')
                if update_fields:
                    profile.save(update_fields=update_fields)
            # Persist the language and the timezone for the entire session.
            request.session[translation.LANGUAGE_SESSION_KEY] = language_code
            request.session['timezone'] = timezone_name
        # Redirect to the URL specified by the `next` parameter or fall back
        # to the URL from the Referer header. For AJAX requests, return a 204
        # status code (No Content) if the `next` parameter is not set. See:
        # https://docs.djangoproject.com/en/1.11/topics/i18n/translation/#the-set-language-redirect-view
        redirect_url = self.get_redirect_url(fallback=(not request.is_ajax()))
        if not redirect_url:
            if request.is_ajax():
                return http.HttpResponse(status=204)
            else:
                redirect_url = '/'
        return http.HttpResponseRedirect(redirect_url)
