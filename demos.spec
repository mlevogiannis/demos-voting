%define git_repo demos
%define git_head HEAD

# Since we are a standalone app, install at datadir
%global    app_dir      %{_datadir}/%{name}
%global    app_bindir   %{_libdir}/%{name}

%global    with_apache 1

%{!?_webappconfdir: %global _webappconfdir %{_sysconfdir}/httpd/conf.d/ }

Summary:	Secure voting platform
Name:		demos-voting
Version:	%git_get_ver
Release:	%mkrel %git_get_rel2
Source:		%git_bs_source %{name}-%{version}.tar.gz
Source1:	%{name}-gitrpm.version
Source2:	%{name}-changelog.gitrpm.txt
License:	Other
Group:		Applications/Web
# Url:		
BuildRequires:	python-setuptools
BuildRequires:  python-devel
BuildRequires: protobuf-devel, protobuf-compiler
BuildRequires: systemd-units

%package common
Summary:        Common files for Secure Voting platform
Group:          Applications/Web
BuildArch:      noarch
Requires:       python-django >= 1.8
Requires:       python-psycopg2
Requires:       python-requests
Requires:       python-six >= 1.9.0
Requires:       python-celery
%if %{with_apache}
%if %{_target_vendor} == mageia
Requires:       apache-mod_wsgi
Requires:       apache-mod_ssl
%else
# RedHat variants:
Requires:       mod_wsgi
Requires:       mod_ssl
%endif
# else
#     TODO: nginx etc. support
%endif


%package abb
Summary:        Audit Bulletin Board for Secure Voting
Group:          Applications/Web
BuildArch:      noarch
Requires:       %{name}-common == %{version}
Requires:       python-protobuf >= 3.0

%package ea
Summary:        Election Authority for Secure Voting
Group:          Applications/Web
# no BuildArch, this one is platform-dependant!
Requires:       %{name}-common == %{version}
Requires:       fontconfig
Requires:       python-protobuf >= 3.0
Requires:       python-qrcode
Requires:       python-reportlab
Requires:       liberation-sans-fonts, liberation-serif-fonts, liberation-mono-fonts

%package bds
Summary:        Ballot Distribution Server for Secure Voting
Group:          Applications/Web
BuildArch:      noarch
Requires:       %{name}-common == %{version}

%package vbb
Summary:        Vote Bulletin Board for Secure Voting
Group:          Applications/Web
BuildArch:      noarch
Requires:       %{name}-common == %{version}
Requires:       fontconfig


%description
TODO!

In order to preserve cryptographic integrity, individual sub-packages
MUST be installed on separate servers, that do NOT share their storage.


%description common

sdafadsf


%description abb

sdafadsf


%description ea

sdafadsf

%description bds

sdafadsf

%description vbb

sdafadsf



%prep
%git_get_source
%setup -q

%build
pushd demos-crypto/src
    %make
popd

%install
%__rm -rf %{buildroot}
install -d %{buildroot}%{app_bindir}/
install demos-crypto/src/demos-crypto %{buildroot}%{app_bindir}/

install -d %{buildroot}%{app_dir}
cp -r demos/demos %{buildroot}%{app_dir}
cp demos/manage.py %{buildroot}%{app_dir}

# But, since the settings file is to be edited, move it to /etc
install -d %{buildroot}%{_sysconfdir}/%{name}/
rm -f %{buildroot}%{app_dir}/settings/base.py?
mv %{buildroot}%{app_dir}/demos/settings/base.py %{buildroot}%{_sysconfdir}/%{name}/settings.py
ln -s %{_sysconfdir}/%{name}/settings.py %{buildroot}%{app_dir}/demos/settings/base.py

%if %{with_apache}
# Configuration for Apache and its mod_wsgi
install -d %{buildroot}%{_webappconfdir}

cat '-' <<EOF > %{buildroot}%{_webappconfdir}/30-%{name}.conf
# Note: installing %{name} as main application of this site

<VirtualHost *:80>
    # ServerName our.voting.com
    # Redirect permanent / https://our.voting.com/
</VirtualHost>

WSGIPythonPath %{app_dir}/

<VirtualHost *:443>
    # ServerName our.voting.com
    
    ErrorLog logs/ssl_error_log
    TransferLog logs/ssl_access_log
    LogLevel warn

    SSLEngine on
    SSLProtocol all -SSLv2
    SSLCipherSuite HIGH:MEDIUM:!aNULL:!MD5

    SSLCertificateFile /etc/pki/tls/certs/localhost.crt
    SSLCertificateKeyFile /etc/pki/tls/private/localhost.key

    Alias /robots.txt %{app_dir}/static/robots.txt
    Alias /favicon.ico %{app_dir}/static/favicon.ico

    Alias /media/ %{app_dir}/media/
    Alias /static/ %{app_dir}/static/

    WSGIScriptAlias / %{app_dir}/demos/wsgi.py

    <Directory %{app_dir}/static>
        Require all granted
    </Directory>

    <Directory %{app_dir}/media>
        Require all granted
    </Directory>

    <Directory %{app_dir}/demos/>
    <Files wsgi.py>
        Require all granted
    </Files>
    </Directory>

</VirtualHost>

EOF
%endif

install -d %{buildroot}%{_unitdir}/
cat '-' <<EOF > %{buildroot}%{_unitdir}/demos-voting-crypto.service
[Unit]
Description=Demos-Voting Crypto
After=network.service
Requisite=network.service

[Service]
Type=simple
User=apache
RestartSec=10
TimeoutStartSec=1min
ExecStart=%{app_bindir}/demos-crypto -s unix /tmp/demos-ea-crypto.sock

[Install]
WantedBy=default.target

EOF


%post ea
NEW_SECRET_KEY=$(python -c 'import os; import base64; print("'" + base64.b64encode(os.urandom(60)) + "'" )')
sed -i "s|NO_SECRET_KEY_DEFINED|$NEW_SECRET_KEY|" %{_sysconfdir}/%{name}/settings.py
sed -i "s|NO_APP_CHOSEN|('ea',)|" %{_sysconfdir}/%{name}/settings.py

cd %{app_dir}
./manage.py collectstatic --noinput --no-color
./manage.py compilemessages --no-color


%post bds
NEW_SECRET_KEY=$(python -c 'import os; import base64; print("'" + base64.b64encode(os.urandom(60)) + "'" )')
sed -i "s|NO_SECRET_KEY_DEFINED|$NEW_SECRET_KEY|" %{_sysconfdir}/%{name}/settings.py
sed -i "s|NO_APP_CHOSEN|('bds',)|" %{_sysconfdir}/%{name}/settings.py

cd %{app_dir}
./manage.py collectstatic --noinput --no-color
./manage.py compilemessages --no-color

%post abb
NEW_SECRET_KEY=$(python -c 'import os; import base64; print("'" + base64.b64encode(os.urandom(60)) + "'" )')
sed -i "s|NO_SECRET_KEY_DEFINED|$NEW_SECRET_KEY|" %{_sysconfdir}/%{name}/settings.py
sed -i "s|NO_APP_CHOSEN|('abb',)|" %{_sysconfdir}/%{name}/settings.py

cd %{app_dir}
./manage.py collectstatic --noinput --no-color
./manage.py compilemessages --no-color

%post vbb
NEW_SECRET_KEY=$(python -c 'import os; import base64; print("'" + base64.b64encode(os.urandom(60)) + "'" )')
sed -i "s|NO_SECRET_KEY_DEFINED|$NEW_SECRET_KEY|" %{_sysconfdir}/%{name}/settings.py
sed -i "s|NO_APP_CHOSEN|('vbb',)|" %{_sysconfdir}/%{name}/settings.py

cd %{app_dir}
./manage.py collectstatic --noinput --no-color
./manage.py compilemessages --no-color


%files common
%doc demos/LICENSE demos/README
%dir %{app_dir}/demos
%dir %attr(0755,root,root) %{_sysconfdir}/%{name}/
%config(noreplace) %attr(0755,root,root) %{_sysconfdir}/%{name}/settings.py
%exclude %{_sysconfdir}/%{name}/settings.py?
%{app_dir}/demos/__init__.py*
%{app_dir}/demos/apps/__init__.py*
%{app_dir}/demos/urls.py*
%attr(0755,root,apache) %{app_dir}/demos/wsgi.py*
%{app_dir}/manage.py*
%{app_dir}/demos/common/
%{app_dir}/demos/settings
%if %{with_apache}
%config(noreplace) %{_webappconfdir}/30-%{name}.conf
%endif

%files abb
%{app_dir}/demos/apps/abb/

%files ea
%{app_bindir}/demos-crypto
%{app_dir}/demos/apps/ea/
%config %{_unitdir}/demos-voting-crypto.service

%files bds
%{app_dir}/demos/apps/bds/

%files vbb
%{app_dir}/demos/apps/vbb/


%changelog -f %{_sourcedir}/%{name}-changelog.gitrpm.txt
