from __future__ import absolute_import, division, print_function, unicode_literals

import pytz

from django.utils import timezone


class TimezoneMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone_name = request.session.get('timezone')
        if timezone_name is not None and timezone_name in pytz.all_timezones_set:
            timezone.activate(timezone_name)
        else:
            timezone.deactivate()
        return self.get_response(request)
