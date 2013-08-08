# Copyright 2012,2013 Christoph Reiter
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

from __future__ import print_function

import os
import unittest
import logging
import platform

_gi_version = (-1)
_is_gi = False
_is_pypy = False
_has_cairo = False
_fixme = {}


def skipUnlessGIVersion(*version):
    return unittest.skipIf(_is_gi and _gi_version < version, "gi too old")


def skipIfGI(func):
    if callable(func):
        return unittest.skipIf(_is_gi, "not supported by gi")(func)
    else:
        assert isinstance(func, basestring)

        def wrap(f):
            return unittest.skipIf(_is_gi, func)(f)
        return wrap


def skipIfPyPy(message):

    def wrap(f):
        _fixme[f] = "PyPy: %s" % message
        return unittest.skipIf(_is_pypy, message)(f)
    return wrap


def skipUnlessCairo(func):
    return unittest.skipIf(_has_cairo, "not cairo")(func)


def FIXME(func):
    if callable(func):
        _fixme[func] = None
        return unittest.skip("FIXME")(func)
    else:
        assert isinstance(func, basestring)

        def wrap(f):
            _fixme[f] = func
            return unittest.skip("FIXME")(f)
        return wrap


def test(load_gi, backend=None, strict=False, filter_=None):
    """Run the test suite.

    load_gi -- run all tests in the pygobject suite with PyGObject
    backend -- "ctypes" or "cffi"
    strict  -- fail on glib warnings
    filter_ -- filter for test names (class names)
    """

    global _is_gi, _is_pypy, _has_cairo, _gi_version

    _is_gi = load_gi
    _is_pypy = platform.python_implementation() == "PyPy"

    if not load_gi:
        try:
            import cairocffi
            cairocffi.install_as_pycairo()
        except ImportError:
            pass
        import pgi
        pgi.install_as_gi()
        try:
            pgi.set_backend(backend)
        except LookupError:
            print("Couldn't load backend: %r" % backend)
            return

    def headline(text):
        return (("### %s " % text) + "#" * 80)[:80]

    import gi
    if load_gi:
        assert gi.__name__ == "gi"
        _gi_version = gi._gobject.pygobject_version
        hl = headline("GI")
    else:
        assert gi.__name__ == "pgi"
        if backend:
            hl = headline("PGI (%s)" % backend)
        else:
            hl = headline("PGI")
    print(hl[:80])

    if load_gi:
        _has_cairo = True
    else:
        _has_cairo = gi.check_foreign("cairo", "Context") is not None

    # gi uses logging
    logging.disable(logging.ERROR)

    if strict:
        # make glib warnings fatal
        from gi.repository import GLib
        GLib.log_set_always_fatal(
            GLib.LogLevelFlags.LEVEL_CRITICAL |
            GLib.LogLevelFlags.LEVEL_ERROR |
            GLib.LogLevelFlags.LEVEL_WARNING)

    current_dir = os.path.join(os.path.dirname(__file__))

    tests = []

    loader = unittest.TestLoader()
    tests.extend(loader.discover(os.path.join(current_dir, "pygobject")))

    if not load_gi:
        loader = unittest.TestLoader()
        tests.extend(loader.discover(os.path.join(current_dir, "pgi")))

    def flatten_tests(suites):
        tests = []
        try:
            for suite in suites:
                tests.extend(flatten_tests(suite))
        except TypeError:
            return [suites]
        return tests

    tests = flatten_tests(tests)
    if filter_ is not None:
        tests = filter(lambda t: filter_(t.__class__.__name__), tests)

    # collected by the FIXME decorator
    print(headline("FIXME"))
    for item, desc in sorted(_fixme.items()):
        print(" -> %s.%s" % (item.__module__, item.__name__), end="")
        if desc:
            print("(%s)" % desc)
        else:
            print()

    run = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(tests))

    return len(run.failures) + len(run.errors)
