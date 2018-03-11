from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.utils import translation
from django.utils.translation import ugettext as _

from demos_voting.base.forms import SetLanguageAndTimezoneForm
from demos_voting.base.utils import get_site_url, installed_app_labels

PROJECT_URLS = {
    'en': 'http://www-en.demos-voting.org',
    'el': 'http://www.demos-voting.org',
}

SOURCE_CODE_URL = 'https://github.com/mlevogiannis/demos-voting'


def base(request):
    # Prepare the header's navigation bar. If exactly one application is
    # installed (the default in production instances) then it is always
    # assumed to be the active application. In this case, force the main
    # navigation bar to the active application's navigation bar (so that
    # the account and error pages have a navigation bar).
    if len(installed_app_labels) == 1:
        active_app_label = installed_app_labels[0]
        main_nav = '%s/includes/nav.html' % active_app_label
    else:
        active_app_label = request.resolver_match.app_name.replace('-', '_')
        main_nav = ''
    header_nav = [
        (verbose_name, settings.DEMOS_VOTING_URLS[app_label], app_label == active_app_label)
        for app_label, verbose_name in [
            ('election_authority', _("Election Authority")),
            ('ballot_distributor', _("Ballot Distributor")),
            ('vote_collector', _("Vote Collector")),
            ('bulletin_board', _("Bulletin Board")),
        ]
    ]
    # Get the project website's URL in the active language, falling back to
    # English if it is not available.
    project_url = PROJECT_URLS.get(translation.get_language(), PROJECT_URLS['en'])
    # Force timezone detection if the `timezone` key is not in the session.
    detect_timezone = ('timezone' not in request.session)
    set_language_and_timezone_form = SetLanguageAndTimezoneForm()
    # Return the context data.
    return {
        'site_name': settings.DEMOS_VOTING_SITE_NAME,
        'site_logo': settings.DEMOS_VOTING_SITE_LOGO,
        'header_nav': header_nav,
        'main_nav': main_nav,
        'site_url': get_site_url(request),
        'project_url': project_url,
        'source_code_url': SOURCE_CODE_URL,
        'detect_timezone': detect_timezone,
        'set_language_and_timezone_form': set_language_and_timezone_form,
    }
