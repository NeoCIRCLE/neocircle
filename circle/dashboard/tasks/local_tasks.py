# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

from manager.mancelery import celery


@celery.task(bind=True)
def lazy_evaluator(task, cls, pk, prop):
    obj = cls.objects.get(pk=pk)
    for i in prop.split("."):
        if i.endswith("()"):
            prop = prop[:-2]
            call = True
        else:
            call = False
        obj = getattr(obj, prop)
        if call:
            obj = obj()
    return obj


@celery.task(bind=True)
def lazy_column(task, cls, clsargs, clskwargs, kwargs):
    obj = cls(*clsargs, **clskwargs)
    # skip over LazyColumnMixin.render
    assert cls.__mro__[0].__name__ == "LazyColumnMixin"
    return cls.__mro__[1].render(obj, **kwargs)
