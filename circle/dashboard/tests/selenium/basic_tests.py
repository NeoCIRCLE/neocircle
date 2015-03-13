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
import logging
from sys import stdout
import random
import re
import urlparse

from django.contrib.auth.models import User
from django.db.models import Q

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenose.cases import SeleniumTestCase

from vm.models import Instance
from .config import SeleniumConfig
from .util import CircleSeleniumMixin, SeleniumMixin

logger = logging.getLogger(__name__)
consoleHandler = logging.StreamHandler(stdout)
logger.addHandler(consoleHandler)
conf = SeleniumConfig()


class BasicSeleniumTests(SeleniumTestCase, SeleniumMixin, CircleSeleniumMixin):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.conf = conf
        self.template_ids = []
        self.vm_ids = []

    @classmethod
    def setup_class(cls):
        if conf.create_user:
            cls._user = User.objects.create(username=conf.client_name,
                                            is_superuser=True)
            cls._user.set_password(conf.random_pass)
            cls._user.save()

    @classmethod
    def teardown_class(cls):
        if conf.create_user:
            for instance in Instance.objects.all().filter(
                    ~Q(status=u'DESTROYED'), owner=cls._user):
                instance.destroy(system=True)
            cls._user.delete()

    def test_01_login(self):
        title = 'Dashboard | CIRCLE'
        location = '/dashboard/'
        self.login()
        self.driver.get('%s/dashboard/' % conf.host)
        url = urlparse.urlparse(self.driver.current_url)
        (self.assertIn('%s' % title, self.driver.title,
                       '%s is not found in the title' % title) or
            self.assertEqual(url.path, '%s' % location,
                             'URL path is not equal with %s' % location))

    def test_02_add_template_rights(self):
        self.login()
        template_pool = self.get_template_id(from_all=True)
        if len(template_pool) > 1:
            chosen = template_pool[random.randint(0, len(template_pool) - 1)]
        elif len(template_pool) == 1:
            chosen = template_pool[0]
        else:
            logging.warning("Selenium did not found any templates")
            logging.exception(
                "System did not meet required conditions to continue")
        self.driver.get('%s/dashboard/template/%s/' % (conf.host, chosen))
        acces_form = self.driver.find_element_by_css_selector(
            "form[action*='/dashboard/template/%(template_id)s/acl/']"
            "[method='post']" % {
                'template_id': chosen})
        user_name = acces_form.find_element_by_css_selector(
            "input[type='text'][id='id_name']")
        user_status = acces_form.find_element_by_css_selector(
            "select[name='level']")
        user_name.clear()
        user_name.send_keys(conf.client_name)
        self.select_option(user_status, 'user')
        # For strange reasons clicking on submit button doesn't work anymore
        acces_form.submit()
        found_users = []
        acl_users = self.driver.find_elements_by_css_selector(
            "a[href*='/dashboard/profile/']")
        for user in acl_users:
            user_text = re.split(r':[ ]?', user.text)
            if len(user_text) == 2:
                found_name = re.search(r'[\w\W]+(?=\))', user_text[1]).group()
                logging.info("'%(user)s' found in ACL "
                             "list for template %(id)s" % {
                                 'user': found_name,
                                 'id': chosen})
                found_users.append(found_name)
        self.assertIn(conf.client_name, found_users,
                      "Could not add user to template's ACL")

    def test_03_able_to_create_template(self):
        self.login()
        template_list = None
        create_template = self.get_link_by_href('/dashboard/template/choose/')
        self.click_on_link(create_template)
        WebDriverWait(self.driver, conf.wait_max_sec).until(
            ec.visibility_of_element_located((
                By.ID, 'confirmation-modal')))
        template_list = self.driver.find_elements_by_class_name(
            'template-choose-list-element')
        logging.info('Selenium found %(count)s template possibilities' % {
            'count': len(template_list)})
        (self.assertIsNotNone(
            template_list, "Selenium can not find the create template list") or
            self.assertGreater(len(template_list), 0,
                               "The create template list is empty"))

    def test_04_create_base_template(self):
        self.login()
        created_template_id = self.get_template_id(
            self.create_base_template())
        found = created_template_id is not None
        if found:
            self.template_ids.extend(created_template_id)
        self.assertTrue(
            found,
            "Could not found the created template in the template list")

    def test_05_create_template_from_base(self):
        self.login()
        created_template_id = self.get_template_id(
            self.create_template_from_base())
        found = created_template_id is not None
        if found:
            self.template_ids.extend(created_template_id)
        self.assertTrue(
            found,
            "Could not found the created template in the template list")

    def test_06_delete_templates(self):
        success = False
        self.login()
        for template_id in self.template_ids:
            logging.info("Deleting template %s" % template_id)
            self.delete_template(template_id)
        existing_templates = self.get_template_id()
        if len(existing_templates) == 0:
            success = True
        else:
            for template_id in self.template_ids:
                if template_id not in existing_templates:
                    self.template_ids.remove(template_id)
            if len(self.template_ids) == 0:
                success = True
        self.assertTrue(
            success, "Could not delete (all) the test template(s)")

    def test_07_able_to_create_vm(self):
        self.login()
        vm_list = None
        create_vm_link = self.get_link_by_href('/dashboard/vm/create/')
        create_vm_link.click()
        WebDriverWait(self.driver, conf.wait_max_sec).until(
            ec.visibility_of_element_located((
                By.ID, 'confirmation-modal')))
        vm_list = self.driver.find_elements_by_class_name(
            'vm-create-template-summary')
        logging.info("Selenium found %(vm_number)s virtual machine template "
                     " possibilities" % {
                         'vm_number': len(vm_list)})
        (self.assertIsNotNone(
            vm_list, "Selenium can not find the VM list") or
            self.assertGreater(len(vm_list), 0, "The create VM list is empty"))

    def test_08_create_vm(self):
        self.login()
        pk = self.create_random_vm()
        self.vm_ids.append(pk)
        self.assertIsNotNone(pk, "Can not create a VM")

    def test_09_vm_view_change(self):
        self.login()
        expected_states = ["", "none",
                           "none", "",
                           "block", "none"]
        states = self.view_change("vm")
        logging.info('states: [%s]' % ', '.join(map(str, states)))
        logging.info('expected: [%s]' % ', '.join(map(str, expected_states)))
        self.assertListEqual(states, expected_states,
                             "The view mode does not change for VM listing")

    def test_10_node_view_change(self):
        self.login()
        expected_states = ["", "none",
                           "none", "",
                           "block", "none"]
        states = self.view_change("node")
        logging.info('states: [%s]' % ', '.join(map(str, states)))
        logging.info('expected: [%s]' % ', '.join(map(str, expected_states)))
        self.assertListEqual(states, expected_states,
                             "The view mode does not change for NODE listing")

    def test_11_delete_vm(self):
        self.login()
        succes = True
        for vm in self.vm_ids:
            if not self.delete_vm(vm):
                succes = False
            else:
                self.vm_ids.remove(vm)
        self.assertTrue(succes, "Can not delete all VM")
