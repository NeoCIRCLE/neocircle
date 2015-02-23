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
from selenose.cases import SeleniumTestCase
from django.contrib.auth.models import User
import random
import urlparse
import re
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from datetime import datetime
random_pass = "".join([random.choice(
    '0123456789abcdefghijklmnopqrstvwxyz') for n in xrange(10)])
random_accents = random_pass + "".join([random.choice(
    u"áéíöóúűÁÉÍÖÓÜÚŰ") for n in xrange(5)])
wait_max_sec = 10
host = 'https:127.0.0.1'


class UtilityMixin(object):
    def login(self, username, password='password', location=None):
        driver = self.driver
        if location is None:
            location = '/dashboard/'
        driver.get('%s%s' % (host, location))
        #  Only if we aren't logged in already
        if location not in urlparse.urlparse(self.driver.current_url).path:
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
                try:
                    # If selenium runs only in a small (virtual) screen
                    driver.find_element_by_class_name('navbar-toggle').click()
                    WebDriverWait(self.driver, wait_max_sec).until(
                        EC.element_to_be_clickable((
                            By.CSS_SELECTOR,
                            "a[href*='/dashboard/profile/']")))
                except:
                    time.sleep(0.5)
            except:
                raise Exception('Selenium cannot find the form controls')

    def list_options(self, select):
        try:
            option_dic = {}
            select = Select(select)
            for option in select.options:
                key = option.get_attribute('value')
                if key is not None and key:
                    option_dic[key] = [option.text]
            return option_dic
        except:
            raise Exception(
                'Selenium cannot list the select possibilities')

    def select_option(self, select, what=None):
        try:
            my_choice = None
            options = self.list_options(select)
            select = Select(select)
            if what is not None:
                for key, value in options.iteritems():
                    if what in key:
                        my_choice = key
                    else:
                        if isinstance(value, list):
                            for single_value in value:
                                if what in single_value:
                                    my_choice = key
                        else:
                            if what in value:
                                my_choice = key
            if my_choice is None:
                my_choose_list = options.keys()
                my_choice = my_choose_list[random.randint(
                    0, len(my_choose_list) - 1)]
            select.select_by_value(my_choice)
        except:
            raise Exception(
                'Selenium cannot select the chosen one')

    def get_link_by_href(self, target_href, attributes=None):
        try:
            links = self.driver.find_elements_by_tag_name('a')
            for link in links:
                href = link.get_attribute('href')
                if href is not None and href:
                    if target_href in href:
                        perfect_fit = True
                        if isinstance(attributes, dict):
                            for key, target_value in attributes.iteritems():
                                attr_check = link.get_attribute(key)
                                if attr_check is not None and attr_check:
                                    if target_value not in attr_check:
                                        perfect_fit = False
                        if perfect_fit:
                            return link
        except:
            raise Exception(
                'Selenium cannot find the href=%s link' % target_href)

    def click_on_link(self, link):
        """
        There are situations when selenium built in click() function
        doesn't work as intended, that's when this function is used.
        Fires a click event via javascript injection.
        """
        try:
            #  Javascript function to simulate a click on a link
            javascript = (
                "var link = arguments[0];"
                "var cancelled = false;"
                "if(document.createEvent) {"
                "   var event = document.createEvent(\"MouseEvents\");"
                "   event.initMouseEvent("
                "       \"click\", true, true, window, 0, 0, 0, 0, 0,"
                "       false,false,false,false,0,null);"
                "   cancelled = !link.dispatchEvent(event);"
                "} else if(link.fireEvent) {"
                "   cancelled = !link.fireEvent(\"onclick\");"
                "} if (!cancelled) {"
                "   window.location = link.href;"
                "}")
            self.driver.execute_script("%s" % javascript, link)
        except:
            raise Exception(
                'Selenium cannot inject javascript to the page')

    def wait_and_accept_operation(self, argument=None):
        # try:
            accept = WebDriverWait(self.driver, wait_max_sec).until(
                EC.element_to_be_clickable((
                    By.ID, "op-form-send")))
            if argument is not None:
                possible = self.driver.find_elements_by_css_selector(
                    "div.controls > input[type='text']")
                if isinstance(argument, list):
                    for x in range(0, len(possible)):
                        possible[x].clear()
                        possible[x].send_keys(argument[x % len(argument)])
                else:
                    for form in possible:
                        form.clear()
                        form.send_keys(argument)
            accept.click()
        # except:
        #     raise Exception("Selenium cannot accept the"
        #                     " operation confirmation")

    def create_base_template(self, name=None, architecture="x86-64",
                             method=None, op_system=None, lease=None,
                             network="vm"):
        if name is None:
            name = "template_%s" % random_accents
        if op_system is None:
            op_system = "!os %s" % random_accents
        try:
            self.driver.get('%s/dashboard/template/choose/' % host)
            self.driver.find_element_by_css_selector(
                "input[type='radio'][value='base_vm']").click()
            self.driver.find_element_by_id(
                "template-choose-next-button").click()
            template_name = WebDriverWait(self.driver, wait_max_sec).until(
                EC.visibility_of_element_located((
                    By.ID, 'id_name')))
            template_name.clear()
            template_name.send_keys(name)
            self.select_option(self.driver.find_element_by_id(
                "id_arch"), architecture)
            self.select_option(self.driver.find_element_by_id(
                "id_access_method"), method)
            system_name = self.driver.find_element_by_id("id_system")
            system_name.clear()
            system_name.send_keys(op_system)
            self.select_option(self.driver.find_element_by_id(
                "id_lease"), lease)
            self.select_option(self.driver.find_element_by_id(
                "id_networks"), network)
            self.driver.find_element_by_css_selector(
                "input.btn[type='submit']").click()
            WebDriverWait(self.driver, wait_max_sec).until(
                EC.visibility_of_element_located((
                    By.ID, 'ops')))
            self.click_on_link(self.get_link_by_href('/op/deploy/'))
            self.wait_and_accept_operation()
            self.click_on_link(WebDriverWait(self.driver, wait_max_sec).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR, "a[href$='/op/shut_off/']"))))
            self.wait_and_accept_operation()
            WebDriverWait(self.driver, wait_max_sec).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR, "a[href$='/op/deploy/']")))
            self.click_on_link(self.get_link_by_href('/op/save_as_template/'))
            self.wait_and_accept_operation(name)
            return name
        except:
            raise Exception(
                'Selenium cannot create a base template virtual machine')

    def get_template_id(self, name=None):
        try:
            self.driver.get('%s/dashboard/template/list/' % host)
            templates = self.driver.find_elements_by_css_selector("td.name")
            found_template_ids = []
            for template in templates:
                if name in template.text or name is None:
                    template_link = template.find_element_by_css_selector(
                        "a[data-original-title]")
                    found_template_ids.append(
                        re.search(r'\d+', template_link.get_attribute(
                            'innerHTML')).group())
            if not found_template_ids and name is not None:
                print ("Selenium could not find the specified "
                       "%(name)s template in the list" % {
                           'name': name})
            return found_template_ids
        except:
            raise Exception(
                'Selenium cannot found the template\'s id')

    def check_operation_result(self, operation_id):
        try:
            url_save = self.driver.current_url
            self.driver.get('%(host)s/dashboard/vm/activity/%(id)s/' % {
                'host': host,
                'id': operation_id})
            result = WebDriverWait(self.driver, wait_max_sec).until(
                EC.visibility_of_element_located((
                    By.ID, "activity_status")))
            if (result.text == "success"):
                out = True
            else:
                out = False
            self.driver.get(url_save)
            return out
        except:
            raise Exception(
                'Selenium cannot check the result of an operation')

    def recently(self, timeline_dict, second=90):
        try:
            if isinstance(timeline_dict, dict):
                for key, value in timeline_dict.iteritems():
                    time = datetime.strptime(key, '%Y-%m-%d %H:%M')
                    delta = datetime.now() - time
                    if delta.total_seconds() <= second:
                        return value
        except:
            raise Exception(
                'Selenium cannot filter timeline activities to recent')

    def get_timeline_elements(self, code):
        try:
            self.get_link_by_href("#activity").click()
            activity_dict = {}
            timeline = WebDriverWait(self.driver, wait_max_sec).until(
                EC.visibility_of_element_located((
                    By.ID, "activity-timeline")))
            searched_activity = timeline.find_elements_by_css_selector(
                "div[data-activity-code='%s']" % code)
            print "Found activity list for %s:" % code
            for activity in searched_activity:
                activity_id = activity.get_attribute('data-activity-id')
                activity_text = activity.text
                key = re.search(
                    r'\d+-\d+-\d+ \d+:\d+,', activity_text).group()[:-1]
                print ("%(id)s @ %(activity)s" % {
                    'id': activity_id,
                    'activity': key})
                activity_dict[key] = activity_id
            return activity_dict
        except:
            raise Exception('Selenium cannot find the searched activity')

    def create_template_from_base(self, delete_disk=True, name=None):
        try:
            if name is None:
                name = "template_from_base_%s" % random_accents
            self.driver.get('%s/dashboard/template/choose/' % host)
            choice_list = []
            choices = self.driver.find_elements_by_css_selector(
                "input[type='radio']")
            choice_list = [item for item in choices if (
                'test' not in item.get_attribute('value')
                and item.get_attribute('value') != 'base_vm')]
            chosen = random.randint(0, len(choice_list) - 1)
            choice_list[chosen].click()
            self.driver.find_element_by_id(
                "template-choose-next-button").click()
            if delete_disk:
                self.click_on_link(
                    self.get_link_by_href("#resources"))
                disks = WebDriverWait(self.driver, wait_max_sec).until(
                    EC.visibility_of_element_located((
                        By.ID, 'vm-details-resources-disk')))
                disk_list = disks.find_elements_by_css_selector(
                    "h4[class*='list-group-item-heading']")
                if len(disk_list) > 0:
                    self.click_on_link(
                        self.get_link_by_href("/op/remove_disk/"))
                    self.wait_and_accept_operation()
                    WebDriverWait(self.driver, wait_max_sec).until(
                        EC.visibility_of_element_located((
                            By.ID, "_activity")))
                    recent_remove_disk = self.recently(
                        self.get_timeline_elements(
                            "vm.Instance.remove_disk"))
                    if not self.check_operation_result(recent_remove_disk):
                        print ("Selenium cannot delete disk "
                               "of the chosen template")
                        raise Exception('Cannot delete disk')
                    WebDriverWait(self.driver, wait_max_sec).until(
                        EC.element_to_be_clickable((
                            By.CSS_SELECTOR,
                            "a[href$='/op/deploy/']")))
            self.click_on_link(self.get_link_by_href("/op/deploy/"))
            self.wait_and_accept_operation()
            time.sleep(5)
            recent_deploy = self.recently(self.get_timeline_elements(
                "vm.Instance.deploy"))
            if not self.check_operation_result(recent_deploy):
                print ("Selenium cannot deploy the "
                       "chosen template virtual machine")
                raise Exception('Cannot deploy the virtual machine')
            self.click_on_link(WebDriverWait(self.driver, wait_max_sec).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "a[href$='/op/shut_off/']"))))
            self.wait_and_accept_operation()
            time.sleep(2)
            recent_shut_off = self.recently(self.get_timeline_elements(
                "vm.Instance.shut_off"))
            if not self.check_operation_result(recent_shut_off):
                print ("Selenium cannot shut off the "
                       "chosen template virtual machine")
                raise Exception('Cannot shut off the virtual machine')
            self.click_on_link(WebDriverWait(self.driver, wait_max_sec).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "a[href$='/op/save_as_template/']"))))
            self.wait_and_accept_operation(name)
            return name
        except:
            raise Exception('Selenium cannot start a template from a base one')

    def delete_template(self, template_id):
        try:
            self.driver.get('%s/dashboard/template/%s/' % (host, template_id))
            self.click_on_link(
                self.get_link_by_href(
                    "/dashboard/template/delete/%s/" % template_id))
            self.wait_and_accept_operation()
            WebDriverWait(self.driver, wait_max_sec).until(
                EC.visibility_of_element_located((
                    By.CLASS_NAME, 'alert-success')))
            url = urlparse.urlparse(self.driver.current_url)
            if "/template/list/" not in url.path:
                raise Exception()
        except:
            raise Exception('Selenium cannot delete the desired template')

    def create_random_vm(self):
        try:
            self.driver.get('%s/dashboard/vm/create/' % host)
            vm_list = []
            pk = None
            vm_list = self.driver.find_elements_by_class_name(
                'vm-create-template-summary')
            choice = random.randint(0, len(vm_list) - 1)
            vm_list[choice].click()
            WebDriverWait(self.driver, wait_max_sec).until(
                EC.element_to_be_clickable((
                    By.CLASS_NAME, 'vm-create-start'))).click()
            WebDriverWait(self.driver, wait_max_sec).until(
                EC.visibility_of_element_located((
                    By.CLASS_NAME, 'alert-success')))
            url = urlparse.urlparse(self.driver.current_url)
            pk = re.search(r'\d+', url.path).group()
            return pk
        except:
            raise Exception('Selenium cannot start a VM')

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
        self.click_on_link(list_view_link)
        states = [driver.execute_script("%s" % js_script, list_view),
                  driver.execute_script("%s" % js_script, graph_view)]
        self.click_on_link(graph_view_link)
        states.extend([driver.execute_script("%s" % js_script, list_view),
                       driver.execute_script("%s" % js_script, graph_view)])
        self.click_on_link(list_view_link)
        states.extend([driver.execute_script("%s" % js_script, list_view),
                       driver.execute_script("%s" % js_script, graph_view)])
        return states

    def delete_vm(self, pk):
        try:
            driver = self.driver
            driver.get('%s/dashboard/vm/%s/' % (host, pk))
            status_span = driver.find_element_by_id('vm-details-state')
            self.get_link_by_href(
                "/dashboard/vm/%s/op/destroy/" % pk).click()
            WebDriverWait(self.driver, wait_max_sec).until(
                EC.element_to_be_clickable((By.ID, 'op-form-send'))).click()
            WebDriverWait(status_span, wait_max_sec).until(
                EC.visibility_of_element_located((
                    By.CLASS_NAME, 'fa-trash-o')))
            return True
        except:
            raise Exception("Selenium can not destroy a VM")


class VmDetailTest(UtilityMixin, SeleniumTestCase):
    template_ids = []

    @classmethod
    def setup_class(cls):
        cls._user = User.objects.create(username='test_%s' % random_accents,
                                        is_superuser=True)
        cls._user.set_password(random_accents)
        cls._user.save()

    @classmethod
    def teardown_class(cls):
        cls._user.delete()

    # def test_01_login(self):
    #     title = 'Dashboard | CIRCLE'
    #     location = '/dashboard/'
    #     self.login('test_%s' % random_accents, random_accents)
    #     self.driver.get('%s/dashboard/' % host)
    #     url = urlparse.urlparse(self.driver.current_url)
    #     (self.assertIn('%s' % title, self.driver.title,
    #                    '%s is not found in the title' % title) or
    #         self.assertEqual(url.path, '%s' % location,
    #                          'URL path is not equal with %s' % location))

    # def test_02_able_to_create_template(self):
    #     self.login('test_%s' % random_accents, random_accents)
    #     template_list = None
    #     create_template = self.get_link_by_href('/dashboard/template/choose/')
    #     self.click_on_link(create_template)
    #     WebDriverWait(self.driver, wait_max_sec).until(
    #         EC.visibility_of_element_located((
    #             By.ID, 'create-modal')))
    #     template_list = self.driver.find_elements_by_class_name(
    #         'template-choose-list-element')
    #     print 'Selenium found %s template possibilities' % len(template_list)
    #     (self.assertIsNotNone(
    #         template_list, "Selenium can not find the create template list") or
    #         self.assertGreater(len(template_list), 0,
    #                            "The create template list is empty"))

    # def test_03_create_base_template(self):
    #     self.login('test_%s' % random_accents, random_accents)
    #     template_name = self.create_base_template()
    #     self.driver.get('%s/dashboard/template/list/' % host)
    #     templates = self.driver.find_elements_by_css_selector("td.name")
    #     found = False
    #     for template in templates:
    #         if template_name in template.text:
    #             found = True
    #             self.template_ids.append(
    #                 re.search(r'\d+', template.text).group())
    #     self.assertTrue(
    #         found,
    #         "Coud not found the created template in the template list")

    def test_04_create_template_from_base(self):
        self.login('test_%s' % random_accents, random_accents)
        created_template_id = self.get_template_id(
            self.create_template_from_base())
        found = created_template_id is not None
        if found:
            self.template_ids.extend(created_template_id)
        self.assertTrue(
            found,
            "Coud not found the created template in the template list")

    def test_05_delete_templates(self):
        self.login('test_%s' % random_accents, random_accents)
        for template_id in self.template_ids:
            self.delete_template(template_id)
            existing_templates = self.get_template_id()
            for template_id in self.template_ids:
                if template_id not in existing_templates:
                    self.template_ids.remove(template_id)
        self.assertListEqual([], self.template_ids,
                             "Could not delete (all) the test template(s)")


    # def test_10_able_to_create_vm(self):
    #     self.login('test_%s' % random_accents, random_accents)
    #     vm_list = None
    #     create_vm_link = self.get_link_by_href('/dashboard/vm/create/')
    #     create_vm_link.click()
    #     WebDriverWait(self.driver, wait_max_sec).until(
    #         EC.visibility_of_element_located((
    #             By.ID, 'create-modal')))
    #     vm_list = self.driver.find_elements_by_class_name(
    #         'vm-create-template-summary')
    #     print ("Selenium found %(vm_number)s virtual machine template "
    #            " possibilities" % {
    #                'vm_number': len(vm_list)})
    #     (self.assertIsNotNone(
    #         vm_list, "Selenium can not find the VM list") or
    #         self.assertGreater(len(vm_list), 0, "The create VM list is empty"))

    # def test_11_create_vm(self):
    #     self.login('test_%s' % random_accents, random_accents)
    #     pk = self.create_random_vm()
    #     self.assertIsNotNone(pk, "Can not create a VM")

    # def test_12_vm_view_change(self):
    #     self.login('test_%s' % random_accents, random_accents)
    #     expected_states = ["", "none",
    #                        "none", "",
    #                        "block", "none"]
    #     states = self.viewChange("vm")
    #     print 'states: [%s]' % ', '.join(map(str, states))
    #     print 'expected: [%s]' % ', '.join(map(str, expected_states))
    #     self.assertListEqual(states, expected_states,
    #                          "The view mode does not change for VM listing")

    # def test_13_node_view_change(self):
    #     self.login('test_%s' % random_accents, random_accents)
    #     expected_states = ["", "none",
    #                        "none", "",
    #                        "block", "none"]
    #     states = self.viewChange("node")
    #     print 'states: [%s]' % ', '.join(map(str, states))
    #     print 'expected: [%s]' % ', '.join(map(str, expected_states))
    #     self.assertListEqual(states, expected_states,
    #                          "The view mode does not change for NODE listing")

    # def test_14_delete_vm(self):
    #     self.login('test_%s' % random_accents, random_accents)
    #     pk = self.create_random_vm()
    #     self.assertTrue(self.delete_vm(pk), "Can not delete a VM")
