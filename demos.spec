%define git_repo demos
%define git_head HEAD

# Since we are a standalone app, install at datadir
%global    app_dir      %{_datadir}/%{name}
%global    app_bindir   %{_libdir}/%{name}

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

%package common
Summary:        Common files for Secure Voting platform
Group:          Applications/Web
BuildArch:      noarch
Requires:       python-django >= 1.8


%package abb
Summary:        Audit Bulletin Board for Secure Voting
Group:          Applications/Web
BuildArch:      noarch
Requires:       %{name}-common == %{version}

%package ea
Summary:        Election Authority for Secure Voting
Group:          Applications/Web
BuildArch:      noarch
Requires:       %{name}-common == %{version}
Requires:       fontconfig

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
cp -r demos/demos/* %{buildroot}%{app_dir}
cp demos/manage.py %{buildroot}%{app_dir}

# But, since the settings file is to be edited, move it to /etc
install -d %{buildroot}%{_sysconfdir}/%{name}/
rm -f %{buildroot}%{app_dir}/settings/base.py?
mv %{buildroot}%{app_dir}/settings/base.py %{buildroot}%{_sysconfdir}/%{name}/settings.py
ln -s %{_sysconfdir}/%{name}/settings.py %{buildroot}%{app_dir}/settings/base.py


%files common
%doc demos/LICENSE demos/README
%dir %{app_dir}/
%dir %attr(0755,root,root) %{_sysconfdir}/%{name}/
%config(noreplace) %attr(0755,root,root) %{_sysconfdir}/%{name}/settings.py
%exclude %{_sysconfdir}/%{name}/settings.py?
%{app_dir}/__init__.py*
%{app_dir}/apps/__init__.py*
%{app_dir}/urls.py*
%{app_dir}/wsgi.py*
%{app_dir}/manage.py*
%{app_dir}/common/
%{app_dir}/settings


%files abb
%{app_dir}/apps/abb/

%files ea
%{app_bindir}/demos-crypto
%{app_dir}/apps/ea/

%files bds
%{app_dir}/apps/bds/

%files vbb
%{app_dir}/apps/vbb/


%changelog -f %{_sourcedir}/%{name}-changelog.gitrpm.txt
