# -*- coding: utf-8 -*-

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

from arrow import locales


class HungarianLocale(locales.Locale):

    names = ['hu', 'HU']

    past = '{0} ezelőtt'
    future = '{0} múlva'

    timeframes = {
        'now': 'éppen most',
        'seconds': {
            'past': 'másodpercekkel',
            'future': 'pár másodperc'},
        'minute': {'past': 'egy perccel', 'future': 'egy perc'},
        'minutes': {'past': '{0} perccel', 'future': '{0} perc'},
        'hour': {'past': 'egy órával', 'future': 'egy óra'},
        'hours': {'past': '{0} órával', 'future': '{0} óra'},
        'day': {
            'past': 'egy nappal',
            'future': 'egy nap'
        },
        'days': {
            'past': '{0} nappal',
            'future': '{0} nap'
        },
        'month': {'past': 'egy hónappal', 'future': 'egy hónap'},
        'months': {'past': '{0} hónappal', 'future': '{0} hónap'},
        'year': {'past': 'egy évvel', 'future': 'egy év'},
        'years': {'past': '{0} évvel', 'future': '{0} év'},
    }

    month_names = ['', 'Január', 'Február', 'Március', 'Április', 'Május',
                   'Június', 'Július', 'Augusztus', 'Szeptember',
                   'Október', 'November', 'December']
    month_abbreviations = ['', 'Jan', 'Febr', 'Márc', 'Ápr', 'Máj', 'Jún',
                           'Júl', 'Aug', 'Szept', 'Okt', 'Nov', 'Dec']

    day_names = ['', 'Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek',
                 'Szombat', 'Vasárnap']
    day_abbreviations = ['', 'Hét', 'Kedd', 'Szer', 'Csüt', 'Pént',
                         'Szom', 'Vas']

    meridians = {
        'am': 'de',
        'pm': 'du',
        'AM': 'DE',
        'PM': 'DU',
    }

    def _format_timeframe(self, timeframe, delta):
        form = self.timeframes[timeframe]
        if isinstance(form, dict):
            if delta > 0:
                form = form['future']
            else:
                form = form['past']
        delta = abs(delta)

        return form.format(delta)
