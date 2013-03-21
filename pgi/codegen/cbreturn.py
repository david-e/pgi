# Copyright 2013 Christoph Reiter
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

from pgi.gir import GITypeTag


class CallbackReturn(object):
    TAG = None

    @classmethod
    def get_class(cls, type_):
        return cls

    def __init__(self, info, type_):
        self.info = info
        self.type = type_

    def process(self, name):
        return None, name


class BooleanReturn(CallbackReturn):
    TAG = GITypeTag.BOOLEAN


class Int64Return(CallbackReturn):
    TAG = GITypeTag.INT64


class UInt64Return(CallbackReturn):
    TAG = GITypeTag.UINT64


class VoidReturn(CallbackReturn):
    TAG = GITypeTag.VOID

    def process(self, name):
        return None, "None"


_classes = {}


def _find_cbreturn():
    global _classes
    for var in globals().values():
        if not isinstance(var, type):
            continue
        if issubclass(var, CallbackReturn) and var is not CallbackReturn:
            _classes[var.TAG] = var
_find_cbreturn()


def get_cbreturn_class(arg_type):
    global _classes
    tag_value = arg_type.tag.value
    try:
        cls = _classes[tag_value]
    except KeyError:
        raise NotImplementedError(
            "%r callback return not implemented" % arg_type.tag)
    else:
        return cls.get_class(arg_type)
