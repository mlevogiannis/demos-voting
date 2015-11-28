# File: urls.py

from django.conf.urls import include, url
from demos.common.utils import api, base32cf
from demos.apps.bds import views

urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^manage/(?P<election_id>[' + base32cf._valid_re + r']+)/$', views.ManageView.as_view(), name='manage'),
]

apipatterns = [
    url(r'^manage/', include([
        url(r'^setup/$', views.SetupView.as_view(), name='setup'),
        url(r'^update/$', views.UpdateView.as_view(), name='update'),
    ], namespace='manage')),
    url(r'^auth/', include([
        url(r'^login/$', api.login, name='login'),
        url(r'^logout/$', api.logout, name='logout'),
    ], namespace='auth')),
]

