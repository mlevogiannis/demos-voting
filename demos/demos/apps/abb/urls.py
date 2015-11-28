# File: urls.py

from django.conf.urls import include, url
from demos.common.utils import base32cf
from demos.apps.abb import views


urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^audit/(?:(?P<election_id>[' + base32cf._valid_re + r']+)/)?$', \
        views.AuditView.as_view(), name='audit'),
    url(r'^results/(?:(?P<election_id>[' + base32cf._valid_re + r']+)/)?$', \
        views.ResultsView.as_view(), name='results'),
]

apipatterns = [
    url(r'^setup/$', views.SetupView.as_view(), name='setup'),
    url(r'^update/$', views.UpdateView.as_view(), name='update'),
    url(r'^vote/$', views.VoteView.as_view(), name='vote'),
    url(r'^export/', include(views.ExportView.as_patterns(), \
        namespace='export')),
]

