# Copyright 2017 Budapest University of Technology and Economics (BME IK)
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

""" Static files and pipeline configuration. """
# flake8: noqa

from os.path import abspath, dirname, join, normpath, isfile, exists
from util import get_env_variable


########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
BASE_DIR = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(BASE_DIR)
########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(SITE_ROOT, 'media'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = get_env_variable('DJANGO_MEDIA_URL', default='/media/')
########## END MEDIA CONFIGURATION


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(SITE_ROOT, 'static_collected'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = get_env_variable('DJANGO_STATIC_URL', default='/static/')

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)
########## END STATIC FILE CONFIGURATION
STATICFILES_DIRS = [normpath(join(SITE_ROOT, 'bower_components'))]

p = normpath(join(SITE_ROOT, '../../site-circle/static'))
if exists(p):
    STATICFILES_DIRS.append(p)

STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

PIPELINE = {
    'COMPILERS' : ('pipeline.compilers.less.LessCompiler',
                   'pipeline.compilers.es6.ES6Compiler', ),
    'LESS_ARGUMENTS': u'--include-path={}'.format(':'.join(STATICFILES_DIRS)),
    'CSS_COMPRESSOR': 'pipeline.compressors.yuglify.YuglifyCompressor',
    'BABEL_ARGUMENTS': u'--presets env',
    'JS_COMPRESSOR': None,
    'DISABLE_WRAPPER': True,
    'STYLESHEETS': {
        "all": {
            "source_filenames": (
                "compile_bootstrap.less",
                "bootstrap/dist/css/bootstrap-theme.css",
                "fontawesome/css/font-awesome.css",
                "jquery-simple-slider/css/simple-slider.css",
                "intro.js/introjs.css",
                "template.less",
                "dashboard/dashboard.less",
                "network/network.less",
                "autocomplete_light/vendor/select2/dist/css/select2.css",
                "autocomplete_light/select2.css",
            ),
            "output_filename": "all.css",
        },
        "network-editor": {
            "source_filenames": (
                "network/editor.less",
            ),
            "output_filename": "network-editor.css",
        },
    },
    'JAVASCRIPT': {
        "all": {
            "source_filenames": (
                # "jquery/dist/jquery.js",  # included separately
                "bootbox/bootbox.js",
                "bootstrap/dist/js/bootstrap.js",
                "intro.js/intro.js",
                "jquery-knob/dist/jquery.knob.min.js",
                "jquery-simple-slider/js/simple-slider.js",
                "favico.js/favico.js",
                "datatables/media/js/jquery.dataTables.js",
                "autocomplete_light/jquery.init.js",
                "autocomplete_light/autocomplete.init.js",
                "autocomplete_light/vendor/select2/dist/js/select2.js",
                "autocomplete_light/select2.js",
                "jsPlumb/dist/js/dom.jsPlumb-1.7.5-min.js",
                "dashboard/dashboard.js",
                "dashboard/activity.js",
                "dashboard/group-details.js",
                "dashboard/group-list.js",
                "dashboard/js/stupidtable.min.js",  # no bower file
                "dashboard/node-create.js",
                "dashboard/node-details.js",
                "dashboard/node-list.js",
                "dashboard/profile.js",
                "dashboard/store.js",
                "dashboard/template-list.js",
                "dashboard/vm-common.js",
                "dashboard/vm-create.js",
                "dashboard/vm-list.js",
                "dashboard/help.js",
                "js/host.js",
                "js/network.js",
                "js/switch-port.js",
                "js/host-list.js",
            ),
            "output_filename": "all.js",
        },
        "vm-detail": {
            "source_filenames": (
                "clipboard/dist/clipboard.min.js",
                "dashboard/vm-details.js",
                "no-vnc/include/util.js",
                "no-vnc/include/webutil.js",
                "no-vnc/include/base64.js",
                "no-vnc/include/websock.js",
                "no-vnc/include/des.js",
                "no-vnc/include/keysym.js",
                "no-vnc/include/keysymdef.js",
                "no-vnc/include/keyboard.js",
                "no-vnc/include/input.js",
                "no-vnc/include/display.js",
                "no-vnc/include/jsunzip.js",
                "no-vnc/include/rfb.js",
                "dashboard/vm-console.js",
                "dashboard/vm-tour.js",
            ),
            "output_filename": "vm-detail.js",
        },
        "datastore": {
            "source_filenames": (
                "chart.js/dist/Chart.min.js",
                "dashboard/datastore-details.js"
            ),
            "output_filename": "datastore.js",
        },
        "network-editor": {
            "source_filenames": (
                "jsPlumb/dist/js/jsplumb.min.js",
                "network/editor.es6",
            ),
            "output_filename": "network-editor.js",
        },
    },
}
