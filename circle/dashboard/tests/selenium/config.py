#!/usr/bin/env python
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
import random


class SeleniumConfig(object):
    # How many sec can selenium wait till certain parts of a page appears
    wait_max_sec = 10
    # How much sec can pass before the activity is no longer happened recently
    recently_sec = 90
    # Name of the logger (necessary to override test logger)
    logger_name = "selenium"
    # File where the log should be stored
    log_file = "selenium.log"
    # Log file max size in Bytes
    log_size = 1024 * 1024 * 10
    # Format of the log file
    log_format = "%(asctime)s: %(name)s: %(levelname)s:  %(message)s"
    # Backup count of the logfiles
    log_backup = 5

    # Accented letters from which selenium can choose to name stuff
    accents = u"áéíöóúűÁÉÍÖÓÜÚŰ"
    # Non accented letters from which selenium can choose to name stuff
    valid_chars = "0123456789abcdefghijklmnopqrstvwxyz"

    # First we choose 10 random normal letters
    random_pass = "".join([random.choice(
        valid_chars) for n in xrange(10)])
    # Then we append it with 5 random accented one
    random_pass += "".join([random.choice(
        accents) for n in xrange(5)])
    # Then we name our client as test_%(password)s
    client_name = 'test_%s' % random_pass

    # Which webpage should selenium use (localhost is recommended)
    host = 'https://127.0.0.1'
    # In default the tests create a new user then delete it afteword
    # Disable this if selenium cannot acces the database
    create_user = True

    """
    Note: It's possible to setup that selenium uses a distant web server
    for testing. If you choose this method you must provide a distant superuser
    account info for that server by overriding random_pass and client_name by
    uncommenting the lines below.
    """
    # client_name = "user name here"
    # random_pass = "password here"
