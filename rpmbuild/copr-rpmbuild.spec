Name: copr-rpmbuild
Summary: Run COPR build tasks
Version: 0.6
Release: 1%{?dist}
URL: https://pagure.io/copr/copr

# Source is created by:
# git clone https://pagure.io/copr/copr.git
# cd copr/rpmbuild
# tito build --tgz
Source0: %{name}-%{version}.tar.gz

License: GPLv2+
BuildArch: noarch
BuildRequires: python3-devel
BuildRequires: rpm-python3
BuildRequires: asciidoc
Requires: createrepo_c
Requires: dnf-plugins-core
Requires: rpm-python3
Requires: python3
Requires: python3-jinja2
Requires: python3-munch
Requires: python3-lockfile
Requires: python3-configparser
Requires: python3-simplejson

Requires: mock
Requires: git
Requires: expect
Requires: curl

%description
Provides command capable of running COPR build-tasks.
Example: copr-rpmbuild 12345-epel-7-x86_64 will locally
build build-id 12345 for chroot epel-7-x86_64.

%prep
%setup -q

%build
%py3_build
a2x -d manpage -f manpage man/copr-rpmbuild.1.asciidoc

%install
install -d %{buildroot}%{_sysconfdir}/copr-rpmbuild
install -d %{buildroot}%{_sharedstatedir}/copr-rpmbuild
install -d %{buildroot}%{_sharedstatedir}/copr-rpmbuild/results

install -d %{buildroot}%{_bindir}
install -m 755 main.py %{buildroot}%{_bindir}/copr-rpmbuild
install -m 644 main.ini %{buildroot}%{_sysconfdir}/copr-rpmbuild/main.ini
install -m 644 mock.cfg.j2 %{buildroot}%{_sysconfdir}/copr-rpmbuild/mock.cfg.j2
install -m 644 rpkg.conf.j2 %{buildroot}%{_sysconfdir}/copr-rpmbuild/rpkg.conf.j2

install -d %{buildroot}%{_mandir}/man1
install -p -m 644 man/copr-rpmbuild.1 %{buildroot}/%{_mandir}/man1/

%py3_install

%files
%license LICENSE

%{python3_sitelib}/*

%{_bindir}/copr-rpmbuild
%{_mandir}/man1/copr-rpmbuild.1*

%dir %attr(0775, root, mock) %{_sharedstatedir}/copr-rpmbuild
%dir %attr(0775, root, mock) %{_sharedstatedir}/copr-rpmbuild/results

%dir %{_sysconfdir}/copr-rpmbuild
%config(noreplace) %{_sysconfdir}/copr-rpmbuild/main.ini
%config(noreplace) %{_sysconfdir}/copr-rpmbuild/mock.cfg.j2
%config(noreplace) %{_sysconfdir}/copr-rpmbuild/rpkg.conf.j2

%changelog
* Fri Jul 07 2017 clime <clime@redhat.com> 0.6-1
- support for source downloading

* Tue Jun 27 2017 clime <clime@redhat.com> 0.5-1
- use Perl Virtual naming for Requires

* Fri Jun 23 2017 clime <clime@redhat.com> 0.4-1
- use dnf.conf for custom-1 chroots
- also copy .spec to the build result directory
- raise curl timeout for downloading sources to be built
- changes according to review bz#1460630
- rpmbuild_networking option is now used to enable/disable net

* Wed Jun 14 2017 clime <clime@redhat.com> 0.3-1
- support for mock's bootstrap container
- check each line of sources file separately
- allow multiple sources and use current dir for mock as source dir
- also check for value of repos first before array referencing in mockcfg.tmpl
- handle null for buildroot_pkgs in mockcfg.tmpl

* Fri Jun 09 2017 clime <clime@redhat.com> 0.2-1
- new package built with tito

* Fri Jun 02 2017 clime <clime@redhat.com> 0.1-1
- Initial version
