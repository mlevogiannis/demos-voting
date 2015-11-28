# File: urls.py

from django.conf.urls import include, url
from demos.common.utils import base32cf
from demos.apps.bds import views


urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^manage/(?:(?P<election_id>[' + base32cf._valid_re + r']+)/)?$', \
        views.ManageView.as_view(), name='manage'),
]

apipatterns = [
    url(r'^setup/$', views.SetupView.as_view(), name='setup'),
    url(r'^update/$', views.UpdateView.as_view(), name='update'),
]

