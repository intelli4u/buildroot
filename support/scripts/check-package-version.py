#!/usr/bin/env python

from __future__ import print_function

import os
import re
import sys


verbose = 0


def debug(*args):
    if verbose > 0:
        print(*args, file=sys.stderr)


def version_compare(a, b):
    def _ensure(v):
        if re.match('\d+', v):
            return int(v)
        else:
            return v


    if cmp(a, b) == 0:
        return 0

    va = a.split('.')
    vb = b.split('.')
    lva = len(va)
    lvb = len(vb)

    for k in range(min(lva, lvb)):
        vva = _ensure(va[k])
        vvb = _ensure(vb[k])

        ret = cmp(vva, vvb)
        if ret != 0:
            return ret

    return cmp(lva, lvb)


def parse_version(workingdir, module, vfile, pattern):
    def _exists(filename):
        return os.path.exists(os.path.join(workingdir, filename))

    def _ensure_version_string(version):
        vers = version.split('-')
        return re.match('^[vV]?[0-9]+[0-9\.]*[A-Za-z0-9_]+$', vers[0]) is not None

    def _read_line(filename):
        with open(os.path.join(workingdir, filename), 'r') as fp:
            for origin in fp:
                if not origin or origin.startswith('#'):
                    continue

                return origin.strip()

        return ''

    def _read_pattern(filename, pattern=None):
        debug(':: %s - %s' % (filename, pattern))
        with open(os.path.join(workingdir, filename), 'r') as fp:
            for origin in fp:
                line = origin.strip()
                ma = re.match(pattern, line)
                if ma:
                    return ma

        return None

    def _read_item(filename, pattern, id=None):
        match = _read_pattern(filename, pattern)
        if match:
            return match.group(id or 1).strip('\'"').strip()
        else:
            return None

    def _configure_in(name, *args):
        def _ac_init(filename):
            version = ''
            match = _read_item(filename, 'AC_INIT\((.+)\)')
            if match:
                # AC_INIT([gdbm], [1.8.3])
                # AC_INIT([avahi],[0.6.25],[avahi (at) lists (dot) freedesktop (dot) org])
                items = match.split(',')
                if len(items) > 1:
                    version = items[1].strip().strip('[]')

            return version

        def _auto_init_automake(filename):
            version = ''
            match = _read_item(filename, 'AM_INIT_AUTOMAKE\((.+)\)')
            if match:
                # AM_INIT_AUTOMAKE(bridge-utils,1.0.6)
                # AM_INIT_AUTOMAKE(libevent,2.0.20-stable)
                items = match.split(',')
                if len(items) > 1:
                    version = items[1].strip()

                # AM_INIT_AUTOMAKE([1.10 tar-ustar -Wno-portability])
                # AM_INIT_AUTOMAKE([1.11.1 gnu subdir-objects])
                if not version:
                    items = match.split(' ')
                    if len(items) > 1:
                        version = items[0].strip()
                # wget/configure.ac:49:AM_INIT_AUTOMAKE([1.9])
                if not version:
                    version = match

            return version.strip('[]')

        def _define_version(filename):
            return _read_item(filename, 'define\(\[.*VERSION]\s*,\s*\[(.+)\]\)')

        def _my_version(filename):
            return _read_item(filename, 'm4_define\(\[my_version\],\s+\[([^]]+)\]\)')

        version = _ac_init(name)
        if not (version and _ensure_version_string(version)):
            version = _auto_init_automake(name)
        if not (version and _ensure_version_string(version)):
            version = _define_version(name)
        if not (version and _ensure_version_string(version)):
            version = _my_version(name)

        return version

    def _configure(name, pattern=None, *args):
        # dist/configure:731:PACKAGE_VERSION='4.7.25'
        match = _read_item(name, 'PACKAGE_VERSION\s*=\s*(.+)')
        if match:
            return match

        # configure:1720:VERSION=2.7
        match = _read_item(name, 'VERSION\s*=\s*(.+)')
        if match and _ensure_version_string(match):
            return match

        return None

    def _makefile(name, pattern=None, *args):
        versions = list()
        # Makefile:VERSION=1.6.6

        # busybox/Makefile
        # VERSION = 2
        # PATCHLEVEL = 6
        # SUBLEVEL = 36
        # EXTRAVERSION = .4
        for label in ('VERSION', 'PATCHLEVEL', 'SUBLEVEL', 'EXTRAVERSION'):
            version = _read_item(name, "%s\s*=\s*(.+)" % label)
            if version:
                versions.append(version.strip('.'))

        if len(versions) > 0:
            return '.'.join(versions)

        # Makefile:DISTNAME=bzip2-1.0.6
        version = _read_item(name, 'DISTNAME\s*=\s*(.+)')
        if version:
            for item in version.split('-'):
                if _ensure_version_string(item):
                    return item

        return None

    def _version_h(name, pattern=None, *args):
        version = _read_item(name, '#\s*define\s+[A-Za-z_]*VERSION[A-Za-z_]*\s+"([^"]{2,})"')
        if version:
            return version

        return None

    def _version_c(name, pattern=None, *args):
        version = _read_item(name, '.+version(\[\]){0,1}\s*=\s*"([^"]+)"', 2)
        if not version:
            version = _read_item(name, '.+version_str(\[\]){0,1}\s*=\s*"([^"]+)"', 2)
        if not version:
            version = _read_item(name, '.+version_string(\[]){0,1}\s*=\s*"([^"]+)"', 2)
        if version:
            return version

        return None

    def _version_sh(name, pattern=None, *args):
        # version.sh:VERSION_NUMBER=0.9.3
        version = _read_item(name, 'VERSION_NUMBER\s*=\s*(.+)')
        if version and _ensure_version_string(version):
            return version

        return None

    def _version_py(name, pattern=None, *args):
        version = _read_item(name, 'version\s*=\s*"(.+)"')
        if version and _ensure_version_string(version):
            return version

        return None

    def _versison_spec(name, pattern=None, *args):
        # Version: 2.15
        version = _read_item(name, '[Vv]ersion\s*:\s*(.+)')
        if version and _ensure_version_string(version):
            return version

        # %define version 2.0.1
        version = _read_item(name, '%define\s+[Vv]ersion\s+(.+)')
        if version and _ensure_version_string(version):
            return version

        return None

    def _version_texi(name, pattern=None, *args):
        # version.texi:2:@set VERSION 4.0.10
        version = _read_item(name, '@set\s+VERSION\s+(.+)')
        if version and _ensure_version_string(version):
            return version

        return None

    def _version_xml(name, pattern=None, *args):
        # <version>2.9.5</version>
        version = _read_item(name, '<version>(.+)</version>')
        if version and _ensure_version_string(version):
            return version

        return None

    def _news(name, pattern=None, *args):
        # ./NEWS:2:zeroconf-0.9:
        version = _read_item(name, '%s[\- ](.+):.*' % module)
        if version and _ensure_version_string(version):
            return version

        return None

    if _exists('VERSION'):
        return _read_line('VERSION')
    elif _exists('version'):
        return _read_line('version')
    else:
        HANDLER = (
            (('configure.in', 'configure.ac'), _configure_in),
            (('configure',), _configure),
            (('Makefile', 'Makefile.in'), _makefile),
            (('version.h', 'version.h.in', 'revision.h'), _version_h),
            (('version.c', 'version.cc'), _version_c),
            (('version.sh',), _version_sh),
            (('version.py',), _version_py),
            (('version.spec',), _versison_spec),
            (('version.texi',), _version_texi),
            (('NEWS',), _news),
        )

        version = ''
        if vfile:
            if _exists(vfile):
                nfile = os.path.basename(vfile)
                for files, func in HANDLER:
                    for name in files:
                        if nfile == name:
                            version = func(vfile, pattern)
                            if version and _ensure_version_string(version):
                                break

                if not version and pattern:
                    version = _read_item(vfile, pattern)
                    if version and not _ensure_version_string(version):
                        version = ''
                else:
                    for _, func in HANDLER:
                        version = func(vfile, pattern)
                        if version and _ensure_version_string(version):
                            break
        else:
            for files, func in HANDLER:
                for name in files:
                    if _exists(name):
                        version = func(name, pattern)
                        if version and _ensure_version_string(version):
                            break

                if version:
                    break

        return version or ''


def parse_args(args):
    global verbose
    op, version, workingdir, module, vfile, pattern = '', '', '', '', '', None

    k = 0
    while k < len(args):
        if args[k] in ('-lt', '-le', '-eq', '-ne', '-ge', '-gt'):
            op = args[k]
            k += 1
            if k < len(args):
                version = args[k]
        elif args[k].startswith('-v'):
            verbose += 1
            for v in args[k][2:]:
                if v == 'v':
                    verbose += 1
        elif not workingdir:
            workingdir = args[k]
        elif not module:
            module = args[k]
        elif not vfile:
            vfile = args[k]
        elif not pattern:
            pattern = args[k]
        else:
            print('Error: Unknown option or parameter - %s' % args[k])
            sys.exit(1)

        k += 1

    if not workingdir:
        workingdir = os.getcwd()

    return op, version, workingdir, module, vfile, pattern


if __name__ == '__main__':
    op, version, workingdir, module, vfile, pattern = parse_args(sys.argv[1:])
    delegation = parse_version(workingdir, module, vfile, pattern)
    if not op:
        print(delegation or '')
    elif op in ('-h', '--help'):
        print('%s [option] dir [module] [version-file] [pattern] ...' % sys.argv[0])
    else:
        diff = version_compare(version, delegation)
        if op == '-lt':
            exitval = diff >= 0
        elif op == '-le':
            exitval = diff > 0
        elif op == '-eq':
            exitval = diff == 0
        elif op == '-ne':
            exitval = diff != 0
        elif op == '-ge':
            exitval = diff < 0
        elif op == '-gt':
            exitval = diff <= 0
        else:
            exitval = False

        sys.exit(0 if exitval else 1)

    sys.exit(0)

