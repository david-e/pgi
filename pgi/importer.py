# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Provides a custom PEP-302 import hook to load GI libraries"""

import sys
from ctypes import c_char_p, byref, CDLL

from pgi.gir import GIRepositoryPtr
from pgi.glib import GErrorPtr
from pgi import const, module, util, overrides

_versions = {}


def require_version(namespace, version):
    """Set a version for the namespace to be loaded.
    This needs to be called before importing the namespace or any
    namespace that depends on it.
    """

    global _versions

    repo = GIRepositoryPtr()

    namespaces = util.array_to_list(repo.get_loaded_namespaces())

    if namespace in namespaces:
        loaded_version = repo.get_version(namespace)
        if loaded_version != version:
            raise ValueError('Namespace %s is already loaded with version %s' %
                             (namespace, loaded_version))

    if namespace in _versions and _versions[namespace] != version:
        raise ValueError('Namespace %s already requires version %s' %
                         (namespace, _versions[namespace]))

    version_glist = repo.enumerate_versions(namespace)
    available_versions = util.glist_to_list(version_glist, c_char_p)
    if not available_versions:
        raise ValueError('Namespace %s not available' % namespace)

    if version not in available_versions:
        raise ValueError('Namespace %s not available for version %s' %
                         (namespace, version))

    _versions[namespace] = version


def get_required_version(namespace):
    """Returns the version string for the namespace that was previously
    required through 'require_version' or None
    """

    global _versions

    return _versions.get(namespace, None)


def extract_namespace(fullname):
    if not fullname.startswith(const.PREFIX + "."):
        return

    return fullname[len(const.PREFIX) + 1:]


def install_import_hook():
    sys.meta_path.append(Importer())


class Importer(object):
    """Import hook according to http://www.python.org/dev/peps/pep-0302/"""

    def find_module(self, fullname, path):
        name = extract_namespace(fullname)
        if not name:
            return

        if not GIRepositoryPtr().enumerate_versions(name):
            return

        return self

    @util.no_jit
    def load_module(self, fullname):
        global _versions

        namespace = extract_namespace(fullname)
        repository = GIRepositoryPtr()

        if namespace in _versions:
            version = _versions[namespace]
        else:
            glist = repository.enumerate_versions(namespace)
            versions = sorted(util.glist_to_list(glist, c_char_p))
            if not versions:
                raise ImportError("%r not found." % namespace)
            version = versions[-1]

        # Dependency already loaded, skip
        if fullname in sys.modules:
            return sys.modules[fullname]

        error = GErrorPtr()
        repository.require(namespace, version, 0, byref(error))
        if error:
            try:
                raise ImportError(error.contents.message)
            finally:
                error.free()

        library_name = repository.get_shared_library(namespace)
        if not library_name:
            raise ImportError("No shared library found for %r" % namespace)
        library_name = library_name.split(",")[0]

        try:
            library = CDLL(library_name)
        except OSError:
            raise ImportError("Couldn't load %r" % library)

        # Generate bindings, set up lazy attributes
        instance = module.Module(repository, namespace, library)
        instance.__file__ = repository.get_typelib_path(namespace)
        instance._version = version

        # add to module and sys.modules
        setattr(__import__(const.PREFIX, fromlist=[""]), namespace, instance)
        sys.modules[fullname] = instance

        # Import a override module if available.
        overrides.load(namespace, instance)

        return instance
