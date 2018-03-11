from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from demos_voting.base.models import HTTPSignatureKey, UserProfile


class DisableDeleteSelectedActionMixin(object):
    def get_actions(self, request):
        actions = super(DisableDeleteSelectedActionMixin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False


class UserAdmin(DisableDeleteSelectedActionMixin, UserAdmin):
    pass


class UserProfileAdmin(DisableDeleteSelectedActionMixin, admin.ModelAdmin):
    pass


class HTTPSignatureKeyAdmin(admin.ModelAdmin):
    list_display = ('user', 'key_id')


admin.site.register(get_user_model(), UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(HTTPSignatureKey, HTTPSignatureKeyAdmin)
