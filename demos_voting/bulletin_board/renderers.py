from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import renderers


class JSONEncoder(renderers.JSONRenderer.encoder_class):
    def __init__(self, *args, **kwargs):
        kwargs['sort_keys'] = True
        super(JSONEncoder, self).__init__(*args, **kwargs)


class JSONRenderer(renderers.JSONRenderer):
    encoder_class = JSONEncoder


class BrowsableAPIRenderer(renderers.BrowsableAPIRenderer):
    template = 'bulletin_board/api.html'

    def show_form_for_method(self, view, method, request, obj):
        # The behavior of `BrowsableAPIRenderer.show_form_for_method()` is
        # buggy (e.g. it calls viewset's methods without setting the `action`
        # attribute, etc). Since users are not supposed to use the HTML forms
        # to edit any objects, disable this functionality completely.
        return False
