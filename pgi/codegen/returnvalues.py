# Copyright 2012 Christoph Reiter
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

from pgi.gir import GITypeTag, GIInfoType
from pgi.util import import_attribute


class ReturnValue(object):
    TAG = None

    def __init__(self, info, type_, backend):
        super(ReturnValue, self).__init__()
        self.info = info
        self.type = type_
        self.backend = backend

    def process(self, name):
        return None, name

    def is_zero_terminated(self):
        return self.type.is_zero_terminated


class BooleanReturnValue(ReturnValue):
    TAG = GITypeTag.BOOLEAN

    def process(self, name):
        return self.backend.unpack_bool(name)


class VoidReturnValue(ReturnValue):
    TAG = GITypeTag.VOID


class ArrayReturnValue(ReturnValue):
    TAG = GITypeTag.ARRAY

    def process(self, name):
        backend = self.backend
        if self.is_zero_terminated():
            block, var = backend.unpack_array_zeroterm_c(name)
            return block, var


class Utf8ReturnValue(ReturnValue):
    TAG = GITypeTag.UTF8

    def process(self, name):
        backend = self.backend
        return backend.unpack_string(name)


class FilenameReturnValue(Utf8ReturnValue):
    TAG = GITypeTag.FILENAME


class InterfaceReturnValue(ReturnValue):
    TAG = GITypeTag.INTERFACE

    def process(self, name):
        backend = self.backend
        iface = self.type.get_interface()
        iface_type = iface.type.value
        iface_namespace = iface.namespace
        iface_name = iface.name
        iface.unref()

        if iface_type == GIInfoType.ENUM:
            attr = import_attribute(iface_namespace, iface_name)
            return backend.unpack_enum(name, attr)
        elif iface_type == GIInfoType.OBJECT:
            return backend.unpack_object(name)

        return None, name


class GTypeReturnValue(ReturnValue):
    TAG = GITypeTag.GTYPE

    def process(self, name):
        return self.backend.unpack_gtype(name)


_classes = {}


def _find_return_values():
    global _classes
    cls = [a for a in globals().values() if isinstance(a, type)]
    rv = ReturnValue
    retv = [a for a in cls if issubclass(a, rv) and a is not rv]
    _classes = dict(((a.TAG, a) for a in retv))
_find_return_values()


def get_return_class(type_):
    global _classes
    tag_value = type_.tag.value
    return _classes.get(tag_value, ReturnValue)
