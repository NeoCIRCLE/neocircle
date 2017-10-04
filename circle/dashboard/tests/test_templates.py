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

from os import listdir
from os.path import isfile, isdir, join
import unittest

from django.template import Template, Context, VariableDoesNotExist
from django.template.engine import Engine
from django.core.urlresolvers import NoReverseMatch


class TemplateSyntaxTestCase(unittest.TestCase):

    def test_templates(self):
        """Test all templates for syntax errors."""
        for loader in Engine.get_default().template_loaders:
            print(loader)
            self._test_dir(loader.get_template_sources(''))

    def _test_dir(self, dir, path="/"):
        for i in dir:
            i = join(path, str(i))
            if isfile(i):
                self._test_template(join(path, i))
            elif isdir(i):
                print("%s:" % i)
                self._test_dir(listdir(i), i)

    def _test_template(self, path):
        print(path)
        try:
            Template(open(path).read()).render(Context({}))
        except (NoReverseMatch, VariableDoesNotExist, KeyError, AttributeError,
                ValueError, ) as e:
            print(e)
