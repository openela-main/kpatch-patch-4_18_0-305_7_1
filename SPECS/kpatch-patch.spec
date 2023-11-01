# Set to 1 if building an empty subscription-only package.
%define empty_package		0

#######################################################
# Only need to update these variables and the changelog
%define kernel_ver	4.18.0-305.7.1.el8_4
%define kpatch_ver	0.9.3
%define rpm_ver		1
%define rpm_rel		4

%if !%{empty_package}
# Patch sources below. DO NOT REMOVE THIS LINE.
#
# https://bugzilla.redhat.com/1971478
Source100: CVE-2021-32399.patch
#
# https://bugzilla.redhat.com/1975190
Source101: CVE-2021-33909.patch
#
# https://bugzilla.redhat.com/1975762
Source102: CVE-2021-22543.patch
#
# https://bugzilla.redhat.com/1980520
Source103: CVE-2021-22555.patch
#
# https://bugzilla.redhat.com/1975066
Source104: CVE-2021-3609.patch
#
# https://bugzilla.redhat.com/1988230
Source105: CVE-2021-37576.patch
#
# https://bugzilla.redhat.com/1981706
Source106: CVE-2020-36385.patch
#
# https://bugzilla.redhat.com/1979028
Source107: CVE-2021-0512.patch
# End of patch sources. DO NOT REMOVE THIS LINE.
%endif

%define sanitized_rpm_rel	%{lua: print((string.gsub(rpm.expand("%rpm_rel"), "%.", "_")))}
%define sanitized_kernel_ver   %{lua: print((string.gsub(string.gsub(rpm.expand("%kernel_ver"), '.el8_?\%d?', ""), "%.", "_")))}
%define kernel_ver_arch        %{kernel_ver}.%{_arch}

Name:		kpatch-patch-%{sanitized_kernel_ver}
Version:	%{rpm_ver}
Release:	%{rpm_rel}%{?dist}

%if %{empty_package}
Summary:	Initial empty kpatch-patch for kernel-%{kernel_ver_arch}
%else
Summary:	Live kernel patching module for kernel-%{kernel_ver_arch}
%endif

Group:		System Environment/Kernel
License:	GPLv2
ExclusiveArch:	x86_64 ppc64le

Conflicts:	%{name} < %{version}-%{release}

Provides:	kpatch-patch = %{kernel_ver_arch}
Provides:	kpatch-patch = %{kernel_ver}

%if !%{empty_package}
Requires:	systemd
%endif
Requires:	kpatch >= 0.6.1-1
Requires:	kernel-uname-r = %{kernel_ver_arch}

%if !%{empty_package}
BuildRequires:	patchutils
BuildRequires:	kernel-devel = %{kernel_ver}
BuildRequires:	kernel-debuginfo = %{kernel_ver}

# kernel build requirements, generated from:
#   % rpmspec -q --buildrequires kernel.spec | sort | awk '{print "BuildRequires:\t" $0}'
# with arch-specific packages moved into conditional block
BuildRequires:	asciidoc audit-libs-devel bash bc binutils binutils-devel bison bzip2 diffutils elfutils elfutils-devel findutils flex gawk gcc gettext git gzip hmaccalc hostname kmod m4 make ncurses-devel net-tools newt-devel numactl-devel openssl openssl-devel patch pciutils-devel perl-Carp perl-devel perl(ExtUtils::Embed) perl-generators perl-interpreter python3-devel python3-docutils redhat-rpm-config rpm-build sh-utils tar xmlto xz xz-devel zlib-devel java-devel kabi-dw

%ifarch x86_64
BuildRequires:	pesign >= 0.10-4
%endif

%ifarch ppc64le
BuildRequires:	gcc-plugin-devel
%endif

Source0:	https://github.com/dynup/kpatch/archive/v%{kpatch_ver}.tar.gz

Source10:	kernel-%{kernel_ver}.src.rpm

# kpatch-build patches

%global _dupsign_opts --keyname=rhelkpatch1

%define builddir	%{_builddir}/kpatch-%{kpatch_ver}
%define kpatch		%{_sbindir}/kpatch
%define kmoddir 	%{_usr}/lib/kpatch/%{kernel_ver_arch}
%define kinstdir	%{_sharedstatedir}/kpatch/%{kernel_ver_arch}
%define patchmodname	kpatch-%{sanitized_kernel_ver}-%{version}-%{sanitized_rpm_rel}
%define patchmod	%{patchmodname}.ko

%define _missing_build_ids_terminate_build 1
%define _find_debuginfo_opts -r
%undefine _include_minidebuginfo
%undefine _find_debuginfo_dwz_opts

%description
This is a kernel live patch module which can be loaded by the kpatch
command line utility to modify the code of a running kernel.  This patch
module is targeted for kernel-%{kernel_ver}.

%prep
%autosetup -n kpatch-%{kpatch_ver} -p1

%build
kdevdir=/usr/src/kernels/%{kernel_ver_arch}
vmlinux=/usr/lib/debug/lib/modules/%{kernel_ver_arch}/vmlinux

# kpatch-build
make -C kpatch-build

# patch module
for i in %{sources}; do
	[[ $i == *.patch ]] && patch_sources="$patch_sources $i"
done
export CACHEDIR="%{builddir}/.kpatch"
kpatch-build/kpatch-build -n %{patchmodname} -r %{SOURCE10} -v $vmlinux --skip-cleanup $patch_sources || { cat "${CACHEDIR}/build.log"; exit 1; }


%install
installdir=%{buildroot}/%{kmoddir}
install -d $installdir
install -m 755 %{builddir}/%{patchmod} $installdir


%files
%{_usr}/lib/kpatch


%post
%{kpatch} install -k %{kernel_ver_arch} %{kmoddir}/%{patchmod}
chcon -t modules_object_t %{kinstdir}/%{patchmod}
sync
if [[ %{kernel_ver_arch} = $(uname -r) ]]; then
	cver="%{rpm_ver}_%{rpm_rel}"
	pname=$(echo "kpatch_%{sanitized_kernel_ver}" | sed 's/-/_/')

	lver=$({ %{kpatch} list | sed -nr "s/^${pname}_([0-9_]+)\ \[enabled\]$/\1/p"; echo "${cver}"; } | sort -V | tail -1)

	if [ "${lver}" != "${cver}" ]; then
		echo "WARNING: at least one loaded kpatch-patch (${pname}_${lver}) has a newer version than the one being installed."
		echo "WARNING: You will have to reboot to load a downgraded kpatch-patch"
	else
		%{kpatch} load %{patchmod}
	fi
fi
exit 0


%postun
%{kpatch} uninstall -k %{kernel_ver_arch} %{patchmod}
sync
exit 0

%else
%description
This is an empty kpatch-patch package which does not contain any real patches.
It is only a method to subscribe to the kpatch stream for kernel-%{kernel_ver}.

%files
%doc
%endif

%changelog
* Wed Oct 27 2021 Artem Savkov <asavkov@redhat.com> [1-4.el8_4]
- out-of-bounds write due to a heap buffer overflow in __hidinput_change_resolution_multipliers() [1979028] {CVE-2021-0512}
- use-after-free in drivers/infiniband/core/ucma.c ctx use-after-free [1981706] {CVE-2020-36385}

* Wed Sep 01 2021 Artem Savkov <asavkov@redhat.com> [1-3.el8_4]
- powerpc: KVM guest OS users can cause host OS memory corruption [1988230] {CVE-2021-37576}

* Tue Jul 27 2021 Artem Savkov <asavkov@redhat.com> [1-2.el8_4]
- race condition in net/can/bcm.c leads to local privilege escalation [1975066] {CVE-2021-3609}
- out-of-bounds write in xt_compat_target_from_user() in net/netfilter/x_tables.c [1980520] {CVE-2021-22555}
- Improper handling of VM_IO|VM_PFNMAP vmas in KVM can bypass RO checks [1975762] {CVE-2021-22543}

* Mon Jul 12 2021 Artem Savkov <asavkov@redhat.com> [1-1.el8_4]
- kernel: size_t-to-int conversion vulnerability in the filesystem layer [1975190] {CVE-2021-33909}
- kernel: race condition for removal of the HCI controller [1971478] {CVE-2021-32399}

* Wed Jun 16 2021 Yannick Cote <ycote@redhat.com> [0-0.el8_4]
- An empty patch to subscribe to kpatch stream for kernel-4.18.0-305.7.1.el8_4 [1972823]
