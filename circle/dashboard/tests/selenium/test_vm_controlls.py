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
from selenose.cases import SeleniumTestCase
from django.contrib.auth.models import User
import random
import urlparse
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
random_pass = "".join([random.choice(
    '0123456789abcdefghijklmnopqrstvwxyz') for n in xrange(10)])
wait_max_sec = 10
host = 'https:127.0.0.1'


class UtilityMixin(object):
    def login(self, username, password='password'):
        driver = self.driver
        driver.get('%s/accounts/login/' % host)
        try:
            name_input = driver.find_element_by_id("id_username")
            password_input = driver.find_element_by_id("id_password")
            submit_input = driver.find_element_by_id("submit-id-submit")
        except:
            inputs = driver.find_elements_by_tag_name("input")
            for current_input in inputs:
                input_type = current_input.get_attribute("type")
                if input_type == "text":
                    name_input = current_input
                if input_type == "password":
                    password_input = current_input
                if input_type == "submit":
                    submit_input = current_input
        try:
            name_input.clear()
            name_input.send_keys(username)
            password_input.clear()
            password_input.send_keys(password)
            submit_input.click()
            try:  # If selenium runs only in a small (virtual) screen
                driver.find_element_by_class_name('navbar-toggle').click()
            except:
                pass
            WebDriverWait(self.driver, wait_max_sec).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR, "a[href*='/dashboard/profile/']")))
        except:
            raise Exception('Selenium cannot find the form controls')

    def get_link_by_href(self, target_href, attributes=None):
        try:
            links = self.driver.find_elements_by_tag_name('a')
            for link in links:
                href = link.get_attribute('href')
                if href is not None:
                    if target_href in href:
                        perfect_fit = True
                        if isinstance(attributes, dict):
                            for key, target_value in attributes.iteritems():
                                attr_check = link.get_attribute(key)
                                if attr_check is not None:
                                    if target_value not in attr_check:
                                        perfect_fit = False
                        if perfect_fit:
                            return link
        except:
            raise Exception(
                'Selenium cannot find the href=%s link' % target_href)

    def create_random_vm(self):
        try:
            self.driver.get('%s/dashboard/vm/create/' % host)
            vm_list = []
            pk = None
            vm_list = self.driver.find_elements_by_class_name(
                'vm-create-template-summary')
            self.driver.save_screenshot('screenie.png')
            choice = random.randint(0, len(vm_list) - 1)
            vm_list[choice].click()
            create = WebDriverWait(self.driver, wait_max_sec).until(
                EC.element_to_be_clickable((
                    By.CLASS_NAME, 'vm-create-start')))
            create.click()
            WebDriverWait(self.driver, wait_max_sec).until(
                EC.visibility_of_element_located((
                    By.CLASS_NAME, 'alert-success')))
            url = urlparse.urlparse(self.driver.current_url)
            pk = re.search(r'\d+', url.path).group()
            return pk
        except:
            raise Exception('Selenium cannot start any VM')

    def viewChange(self, target_box):
        driver = self.driver
        driver.get('%s/dashboard/' % host)
        list_view = driver.find_element_by_id('%s-list-view' % target_box)
        graph_view = driver.find_element_by_id('%s-graph-view' % target_box)
        js_script = 'return arguments[0].style.display;'
        required_attributes = {'data-index-box': target_box}
        graph_view_link = self.get_link_by_href(
            '#index-graph-view',
            required_attributes).find_element_by_tag_name('i')
        list_view_link = self.get_link_by_href(
            '#index-list-view',
            required_attributes).find_element_by_tag_name('i')
        list_view_link.click()
        states = [driver.execute_script("%s" % js_script, list_view),
                  driver.execute_script("%s" % js_script, graph_view)]
        graph_view_link.click()
        states.extend([driver.execute_script("%s" % js_script, list_view),
                       driver.execute_script("%s" % js_script, graph_view)])
        list_view_link.click()
        states.extend([driver.execute_script("%s" % js_script, list_view),
                       driver.execute_script("%s" % js_script, graph_view)])
        return states

    def delete_vm(self, pk):
        try:
            driver = self.driver
            driver.get('%s/dashboard/vm/%s/' % (host, pk))
            status_span = driver.find_element_by_id('vm-details-state')
            destroy_link = self.get_link_by_href(
                "/dashboard/vm/%s/op/destroy/" % pk)
            destroy_link.click()
            destroy = WebDriverWait(self.driver, wait_max_sec).until(
                EC.element_to_be_clickable((By.ID, 'op-form-send')))
            destroy.click()
            WebDriverWait(status_span, wait_max_sec).until(
                EC.visibility_of_element_located((
                    By.CLASS_NAME, 'fa-trash-o')))
            return True
        except:
            raise Exception("Selenium can not destroy a VM")


class VmDetailTest(UtilityMixin, SeleniumTestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='test_%s' % random_pass,
                                      is_superuser=True)
        self.u1.set_password(random_pass)
        self.u1.save()
        self.addCleanup(self.u1.delete)

    def test_01_login(self):
        title = 'Dashboard | CIRCLE'
        location = '/dashboard/'
        self.login('test_%s' % random_pass, random_pass)
        self.driver.get('%s/dashboard/' % host)
        url = urlparse.urlparse(self.driver.current_url)
        (self.assertIn('%s' % title, self.driver.title,
                       '%s is not found in the title' % title) or
            self.assertEqual(url.path, '%s' % location,
                             'URL path is not equal with %s' % location))

    def test_02_able_to_create_vm(self):
        self.login('test_%s' % random_pass, random_pass)
        vm_list = None
        create_vm_link = self.get_link_by_href('/dashboard/vm/create/')
        create_vm_link.click()
        WebDriverWait(self.driver, wait_max_sec).until(
            EC.visibility_of_element_located((
                By.ID, 'create-modal')))
        vm_list = self.driver.find_elements_by_class_name(
            'vm-create-template-summary')
        print 'Selenium found %s template possibilities' % len(vm_list)
        (self.assertIsNotNone(
            vm_list, "Selenium can not find the VM list") or
            self.assertGreater(len(vm_list), 0, "The create VM list is empty"))

    def test_03_create_vm(self):
        self.login('test_%s' % random_pass, random_pass)
        pk = self.create_random_vm()
        self.assertIsNotNone(pk, "Can not create a VM")

    def test_04_vm_view_change(self):
        self.login('test_%s' % random_pass, random_pass)
        expected_states = ["", "none",
                           "none", "",
                           "block", "none"]
        states = self.viewChange("vm")
        print 'states: [%s]' % ', '.join(map(str, states))
        print 'expected: [%s]' % ', '.join(map(str, expected_states))
        self.assertListEqual(states, expected_states,
                             "The view mode does not change for VM listing")

    def test_05_node_view_change(self):
        self.login('test_%s' % random_pass, random_pass)
        expected_states = ["", "none",
                           "none", "",
                           "block", "none"]
        states = self.viewChange("node")
        print 'states: [%s]' % ', '.join(map(str, states))
        print 'expected: [%s]' % ', '.join(map(str, expected_states))
        self.assertListEqual(states, expected_states,
                             "The view mode does not change for NODE listing")

    def test_06_delete_vm(self):
        self.login('test_%s' % random_pass, random_pass)
        pk = self.create_random_vm()
        self.assertTrue(self.delete_vm(pk), "Can not delete a VM")
