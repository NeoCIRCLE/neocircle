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
from datetime import datetime
import inspect
import logging
import random
import re
import time
import urlparse

from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException,
    TimeoutException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from .config import SeleniumConfig

logger = logging.getLogger(SeleniumConfig.logger_name)


class SeleniumMixin(object):
    def create_screenshot(self):
        name = 'ss_from_%(caller_name)s.png' % {
            'caller_name': inspect.stack()[1][3]}
        logger.warning('Creating screenshot "%s"' % name)
        self.driver.save_screenshot(name)

    def get_url(self, fragment_needed=False, fragment=None):
        url_base = urlparse.urlparse(self.driver.current_url)
        url_save = ("%(host)s%(url)s" % {
            'host': self.conf.host,
            'url': urlparse.urljoin(url_base.path, url_base.query)})
        if fragment is None:
            fragment = url_base.fragment
        else:
            fragment_needed = True
        if fragment_needed and fragment:
            url_save = ("%(url)s#%(fragment)s" % {
                'url': url_save,
                'fragment': fragment})
        return url_save

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
            logger.exception("Selenium cannot list the"
                             " select possibilities")
            self.create_screenshot()
            raise Exception(
                'Cannot list the select possibilities')

    def select_option(self, select, what=None):
        """
        From an HTML select imput type try to choose the specified one.
        Select is a selenium web element type. What represent both the
        text of the option and it's ID.
        """
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
            logger.exception("Selenium cannot select the chosen one")
            self.create_screenshot()
            raise Exception(
                'Cannot select the chosen one')

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
            logger.exception(
                "Selenium cannot find the href=%s link" % target_href)
            self.create_screenshot()
            raise Exception('Cannot find the requested href')

    def click_on_link(self, link):
        """
        There are situations when selenium built in click() function
        doesn't work as intended, that's when this function is used.
        Fires a click event via javascript injection.
        """
        try:
            # Javascript function to simulate a click on a link
            javascript = """
                var link = arguments[0];
                var cancelled = false;
                if(document.createEvent) {
                   var event = document.createEvent("MouseEvents");
                   event.initMouseEvent(
                       "click", true, true, window, 0, 0, 0, 0, 0,
                       false,false,false,false,0,null);
                   cancelled = !link.dispatchEvent(event);
                } else if(link.fireEvent) {
                   cancelled = !link.fireEvent("onclick");
                } if (!cancelled) {
                   window.location = link.href;
                }"""
            self.driver.execute_script(javascript, link)
        except:
            logger.exception("Selenium cannot inject javascript to the page")
            self.create_screenshot()
            raise Exception(
                'Cannot inject javascript to the page')

    def get_text(self, node, tag):
        """
        There are some cases where selenium default WebElement text()
        method returns less then it actually could contain. Solving that
        here is a simple regular expression. Give the closest html element
        then specify the html tag of the enclosed text.
        """
        text = ""
        try:
            text_whole = re.search(
                r'<%(tag)s[^>]*>([^<]+)</%(tag)s>' % {
                    'tag': tag},
                node.get_attribute("outerHTML")).group()
            text_parts = text_whole.splitlines()
            for part in text_parts:
                if '<' not in part and '>' not in part:
                    text += part
            text = text.replace(" ", "")
        except:
            return node.text
        if len(node.text) >= len(text):
            text = node.text
        else:
            logger.warning("Better text found which is '%s'" % text)
        return text.strip()


class CircleSeleniumMixin(SeleniumMixin):
    def login(self, location=None):
        driver = self.driver
        if location is None:
            location = '/dashboard/'
        driver.get('%s%s' % (self.conf.host, location))
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
                name_input.send_keys(self.conf.client_name)
                password_input.clear()
                password_input.send_keys(self.conf.random_pass)
                submit_input.click()
                try:
                    # If selenium runs only in a small (virtual) screen
                    driver.find_element_by_class_name('navbar-toggle').click()
                    WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                        ec.element_to_be_clickable((
                            By.CSS_SELECTOR,
                            "a[href*='/dashboard/profile/']")))
                except:
                    time.sleep(0.5)
            except:
                logger.exception("Selenium cannot find the form controls")
                self.create_screenshot()
                raise Exception('Cannot find the form controls')

    def fallback(self, fallback_url, fallback_function):
        logger.warning(
            "However error was anticipated falling back to %(url)s" % {
                'url': fallback_url})
        self.driver.get(fallback_url)
        return fallback_function()

    def wait_and_accept_operation(self, argument=None, try_wait=None,
                                  fallback_url=None):
        """
        Accepts the operation confirmation pop up window.
        Fills out the text inputs before accepting if argument is given.
        """
        try:
            accept = WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                ec.element_to_be_clickable((
                    By.CLASS_NAME, "modal-accept")))
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
            if try_wait is not None:
                WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                    ec.visibility_of_element_located((
                        By.CSS_SELECTOR, try_wait)))
        except TimeoutException:
            logger.exception("Selenium cannot accept the"
                             " operation confirmation")
            if fallback_url is not None:
                self.fallback(
                    fallback_url,
                    lambda: self.wait_and_accept_operation(argument))
            else:
                self.create_screenshot()
                raise Exception(
                    'Cannot accept the operation confirmation')
        except:
            logger.exception("Selenium cannot accept the"
                             " operation confirmation")
            if fallback_url is not None:
                self.fallback(
                    fallback_url,
                    lambda: self.wait_and_accept_operation(argument, try_wait))
            else:
                self.create_screenshot()
                raise Exception(
                    'Cannot accept the operation confirmation')

    def save_template_from_vm(self, name):
        try:
            WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                ec.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "a[href$='/op/deploy/']")))
            url_save = self.get_url()
            self.click_on_link(self.get_link_by_href("/op/deploy/"))
            fallback_url = "%sop/deploy/" % url_save
            self.wait_and_accept_operation(
                try_wait="a[href$='/op/shut_off/']", fallback_url=fallback_url)
            recent_deploy = self.recently(self.get_timeline_elements(
                "vm.Instance.deploy", url_save))
            if not self.check_operation_result(
                    recent_deploy, "a[href*='#activity']"):
                logger.warning("Selenium cannot deploy the "
                               "chosen template virtual machine")
                raise Exception('Cannot deploy the virtual machine')
            self.click_on_link(WebDriverWait(
                self.driver, self.conf.wait_max_sec).until(
                    ec.element_to_be_clickable((
                        By.CSS_SELECTOR,
                        "a[href$='/op/shut_off/']"))))
            fallback_url = "%sop/shut_off/" % url_save
            self.wait_and_accept_operation(
                try_wait="a[href$='/op/deploy/']", fallback_url=fallback_url)
            recent_shut_off = self.recently(self.get_timeline_elements(
                "vm.Instance.shut_off", url_save))
            if not self.check_operation_result(
                    recent_shut_off, "a[href*='#activity']"):
                logger.warning("Selenium cannot shut off the "
                               "chosen template virtual machine")
                raise Exception('Cannot shut off the virtual machine')
            self.click_on_link(WebDriverWait(
                self.driver, self.conf.wait_max_sec).until(
                    ec.element_to_be_clickable((
                        By.CSS_SELECTOR,
                        "a[href$='/op/save_as_template/']"))))
            fallback_url = "%sop/save_as_template/" % url_save
            self.wait_and_accept_operation(
                argument=name, fallback_url=fallback_url)
            recent_save_template = self.recently(self.get_timeline_elements(
                "vm.Instance.save_as_template", url_save))
            if not self.check_operation_result(
                    recent_save_template, "a[href*='#activity']"):
                logger.warning("Selenium cannot save the "
                               "chosen virtual machine as a template")
                raise Exception(
                    'Cannot save the virtual machine as a template')
            logger.warning("Selenium created %(name)s template" % {
                'name': name})
            return name
        except:
            logger.exception("Selenium cannot save a vm as a template")
            self.create_screenshot()
            raise Exception(
                'Cannot save a vm as a template')

    def create_base_template(self, name=None, architecture="x86-64",
                             method=None, op_system=None,
                             datastore="default",
                             lease=None, network="vm"):
        if name is None:
            name = "new_%s" % self.conf.client_name
        if op_system is None:
            op_system = "!os %s" % self.conf.client_name
        try:
            self.driver.get('%s/dashboard/template/choose/' % self.conf.host)
            self.driver.find_element_by_css_selector(
                "input[type='radio'][value='base_vm']").click()
            self.driver.find_element_by_id(
                "template-choose-next-button").click()
            template_name = WebDriverWait(
                self.driver, self.conf.wait_max_sec).until(
                    ec.visibility_of_element_located((
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
                "id_datastore"), datastore)
            self.select_option(self.driver.find_element_by_id(
                "id_lease"), lease)
            self.select_option(self.driver.find_element_by_id(
                "id_networks"), network)
            self.driver.find_element_by_css_selector(
                "input.btn[type='submit']").click()
            return self.save_template_from_vm(name)
        except:
            logger.exception("Selenium cannot create a base"
                             " template virtual machine")
            self.create_screenshot()
            raise Exception(
                'Cannot create a base template virtual machine')

    def get_template_id(self, name=None, from_all=False):
        """
        In default settings find all templates ID in the template list.
        If name is specified searches that specific template's ID
        from_all sets whether to use owned templates or all of them
        Returns list of the templates ID
        """
        try:
            self.driver.get('%s/dashboard/template/list/' % self.conf.host)
            css_selector_of_a_template = ("a[data-original-title]"
                                          "[href*='/dashboard/template/']")
            if from_all:
                self.select_option(self.driver.find_element_by_id(
                    'id_stype'), "all")
                self.driver.find_element_by_css_selector(
                    "button[type='submit']").click()
                try:
                    WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                        ec.presence_of_element_located((
                            By.CSS_SELECTOR, css_selector_of_a_template)))
                except:
                    logger.warning("Selenium could not locate any templates")
                    raise Exception("Could not locate any templates")
            template_table = self.driver.find_element_by_css_selector(
                "table[class*='template-list-table']")
            templates = template_table.find_elements_by_css_selector("td.name")
            found_template_ids = []
            for template in templates:
                # Little magic to outsmart accented naming errors
                template_name = self.get_text(template, "a")
                if name is None or name in template_name:
                    try:
                        template_link = template.find_element_by_css_selector(
                            css_selector_of_a_template)
                        template_id = re.search(
                            r'\d+',
                            template_link.get_attribute("outerHTML")).group()
                        found_template_ids.append(template_id)
                        logger.warning("Found '%(name)s' "
                                       "template's ID as %(id)s" % {
                                           'name': template_name,
                                           'id': template_id})
                    except NoSuchElementException:
                        pass
                    except:
                        raise
                else:
                    logger.warning(
                        "Searching for %(searched)s so"
                        " %(name)s is dismissed" % {
                            'searched': name,
                            'name': template_name})
                    logger.warning(
                        "Dismissed template html code: %(code)s" % {
                            'code': template.get_attribute("outerHTML")})
            if not found_template_ids and name is not None:
                logger.warning("Selenium could not find the specified "
                               "%(name)s template in the list" % {
                                   'name': name})
                raise Exception("Could not find the specified template")
            return found_template_ids
        except:
            logger.exception('Selenium cannot find the template\'s id')
            self.create_screenshot()
            raise Exception(
                'Cannot find the template\'s id')

    def check_operation_result(self, operation_id, restore_selector=None,
                               restore=True):
        """
        Returns wheter the operation_id result is success (returns: boolean)
        """
        try:
            if restore:
                url_save = self.get_url(True)
            self.driver.get('%(host)s/dashboard/vm/activity/%(id)s/' % {
                'host': self.conf.host,
                'id': operation_id})
            result = WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                ec.visibility_of_element_located((
                    By.ID, "activity_status")))
            logger.warning("%(id)s's result is '%(result)s'" % {
                'id': operation_id,
                'result': result.text})
            if (result.text == "success"):
                out = True
            elif (result.text == "wait"):
                time.sleep(2)
                out = self.check_operation_result(
                    operation_id=operation_id, restore=False)
            else:
                try:
                    result_text = WebDriverWait(
                        self.driver, self.conf.wait_max_sec).until(
                            ec.visibility_of_element_located((
                                By.ID, "activity_result_text")))
                    logger.warning(
                        "%(id)s's result text is: '%(result_text)s'" % {
                            'id': operation_id,
                            'result_text': result_text.text})
                except:
                    logger.warning("Cannot read %(id)s's result text" % {
                        'id': operation_id})
                out = False
            if restore:
                logger.warning("Restoring to %s url" % url_save)
                self.driver.get(url_save)
                if restore_selector is not None and restore_selector:
                    WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                        ec.visibility_of_element_located((
                            By.CSS_SELECTOR, restore_selector)))
            return out
        except:
            logger.exception("Selenium cannot check the"
                             " result of an operation")
            self.create_screenshot()
            raise Exception(
                'Cannot check the result of an operation')

    def recently(self, timeline_dict, second=None):
        if second is None:
            second = self.conf.recently_sec
        try:
            if isinstance(timeline_dict, dict):
                recent = None
                for key, value in timeline_dict.iteritems():
                    if recent is None or int(key) > int(recent):
                        recent = key
                if len(timeline_dict) > 1:
                    logger.warning(
                        "Searching for most recent activity"
                        " from the received %(count)s pieces" % {
                            'count': len(timeline_dict)})
                    logger.warning("Found at %(id)s @ %(time)s" % {
                        'id': timeline_dict[recent],
                        'time': datetime.fromtimestamp(
                            int(recent)).strftime('%Y-%m-%d %H:%M:%S')})
                logger.warning(
                    "Checking wheter %(id)s started in the"
                    " recent %(second)s seconds" % {
                        'id': timeline_dict[recent],
                        'second': second})
                delta = datetime.now() - datetime.fromtimestamp(int(recent))
                if delta.total_seconds() <= second:
                    return timeline_dict[recent]
        except:
            logger.exception("Selenium cannot filter timeline "
                             "activities to find most recent")
            self.create_screenshot()
            raise Exception(
                'Cannot filter timeline activities to find most recent')

    def get_timeline_elements(self, code=None, fallback_url=None):
        try:
            if code is None:
                css_activity_selector = "div[data-activity-code]"
                code_text = "all activity"
            else:
                code_text = code
                css_activity_selector = ("div[data-activity-code="
                                         "'%(code)s']" % {
                                             'code': code})
            try:
                self.click_on_link(WebDriverWait(
                    self.driver, self.conf.wait_max_sec).until(
                        ec.element_to_be_clickable((
                            By.CSS_SELECTOR, "a[href*='#activity']"))))
                activity_dict = {}
                timeline = WebDriverWait(
                    self.driver, self.conf.wait_max_sec).until(
                        ec.visibility_of_element_located((
                            By.ID, "activity-timeline")))
                searched_activity = timeline.find_elements_by_css_selector(
                    css_activity_selector)
                logger.warning("Found activity list for %s:" % code_text)
                for activity in searched_activity:
                    activity_id = activity.get_attribute('data-activity-id')
                    key = activity.get_attribute('data-timestamp')
                    logger.warning("%(id)s @ %(activity)s" % {
                        'id': activity_id,
                        'activity': datetime.fromtimestamp(
                            int(key)).strftime('%Y-%m-%d %H:%M:%S')})
                    activity_dict[key] = activity_id
            except StaleElementReferenceException:
                logger.warning('Timeline changed while processing it')
                return self.get_timeline_elements(code, fallback_url)
            except TimeoutException:
                logger.warning('Can not found timeline in the page')
                if fallback_url is not None:
                    return self.fallback(
                        fallback_url,
                        lambda: self.get_timeline_elements(code))
                else:
                    self.create_screenshot()
                    raise Exception('Selenium could not locate the timeline')
            except:
                logger.exception('Selenium cannot get timeline elemets')
                self.create_screenshot()
                raise Exception('Cannot get timeline elements')
            if len(activity_dict) == 0:
                logger.warning('Found activity list is empty')
                self.create_screenshot()
                raise Exception('Selenium did not found any activity')
            return activity_dict
        except:
            logger.exception('Selenium cannot find the searched activity')
            self.create_screenshot()
            raise Exception('Cannot find the searched activity')

    def create_template_from_base(self, delete_disk=True, name=None):
        try:
            if name is None:
                name = "from_%s" % self.conf.client_name
            self.driver.get('%s/dashboard/template/choose/' % self.conf.host)
            choice_list = []
            choices = self.driver.find_elements_by_css_selector(
                "input[type='radio']")
            choice_list = [item for item in choices if (
                'test' not in item.get_attribute('value') and
                item.get_attribute('value') != 'base_vm')]
            chosen = random.randint(0, len(choice_list) - 1)
            choice_list[chosen].click()
            self.driver.find_element_by_id(
                "template-choose-next-button").click()
            if delete_disk:
                url_save = self.get_url(fragment='activity')
                self.click_on_link(
                    self.get_link_by_href("#resources"))
                disks = WebDriverWait(
                    self.driver, self.conf.wait_max_sec).until(
                        ec.visibility_of_element_located((
                            By.ID, 'vm-details-resources-disk')))
                disk_list = disks.find_elements_by_css_selector(
                    "h4[class*='list-group-item-heading']")
                if len(disk_list) > 0:
                    self.click_on_link(
                        self.get_link_by_href("/op/remove_disk/"))
                    self.wait_and_accept_operation(
                        try_wait="a[href*='#activity']")
                    recent_remove_disk = self.recently(
                        self.get_timeline_elements(
                            "vm.Instance.remove_disk", url_save))
                    if not self.check_operation_result(
                            recent_remove_disk, "a[href*='#activity']"):
                        logger.warning("Selenium cannot delete disk "
                                       "of the chosen template")
                        raise Exception('Cannot delete disk')
                return self.save_template_from_vm(name)
        except:
            logger.exception("Selenium cannot start a"
                             " template from a base one")
            self.create_screenshot()
            raise Exception(
                'Cannot start a template from a base one')

    def delete_template(self, template_id):
        try:
            self.driver.get(
                '%s/dashboard/template/%s/' % (self.conf.host, template_id))
            url_save = "%(host)s/dashboard/template/delete/%(pk)s/" % {
                'host': self.conf.host,
                'pk': template_id}
            self.click_on_link(
                self.get_link_by_href(
                    "/dashboard/template/delete/%s/" % template_id))
            self.wait_and_accept_operation(fallback_url=url_save)
            WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                ec.visibility_of_element_located((
                    By.CLASS_NAME, 'alert-success')))
            url = urlparse.urlparse(self.driver.current_url)
            if "/template/list/" not in url.path:
                logger.warning('CIRCLE does not redirect to /template/list/')
                raise Exception(
                    'System does not redirect to template listing')
            logger.warning('Successfully deleted template: id - %(pk)s' % {
                'pk': template_id})
        except:
            logger.exception("Selenium cannot delete the desired template")
            self.create_screenshot()
            raise Exception('Cannot delete the desired template')

    def create_random_vm(self):
        try:
            self.driver.get('%s/dashboard/vm/create/' % self.conf.host)
            vm_list = []
            pk = None
            vm_list = self.driver.find_elements_by_class_name(
                'vm-create-template-summary')
            choice = random.randint(0, len(vm_list) - 1)
            vm_list[choice].click()
            try:
                WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                    ec.element_to_be_clickable((
                        By.CLASS_NAME, "vm-create-start"))).click()
            except TimeoutException:
                # Selenium can time out not findig it even though it is present
                self.driver.find_element_by_tag_name('form').submit()
            except:
                logger.exception("Selenium could not submit create vm form")
                raise Exception('Could not submit a form')
            WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                ec.visibility_of_element_located((
                    By.CLASS_NAME, 'alert-success')))
            url = urlparse.urlparse(self.driver.current_url)
            pk = re.search(r'\d+', url.path).group()
            return pk
        except:
            logger.exception("Selenium cannot start a VM")
            self.create_screenshot()
            raise Exception('Cannot start a VM')

    def view_change(self, target_box):
        driver = self.driver
        driver.get('%s/dashboard/' % self.conf.host)
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
        states = [driver.execute_script(js_script, list_view),
                  driver.execute_script(js_script, graph_view)]
        self.click_on_link(graph_view_link)
        states.extend([driver.execute_script(js_script, list_view),
                       driver.execute_script(js_script, graph_view)])
        self.click_on_link(list_view_link)
        states.extend([driver.execute_script(js_script, list_view),
                       driver.execute_script(js_script, graph_view)])
        return states

    def delete_vm(self, pk):
        try:
            # For relability reasons instead of using the JS operatation
            self.driver.get("%(host)s/dashboard/vm/%(id)s/op/destroy/" % {
                'host': self.conf.host,
                'id': pk})
            self.wait_and_accept_operation(try_wait="a[href*='/op/recover/']")
            try:
                status_span = WebDriverWait(
                    self.driver, self.conf.wait_max_sec).until(
                        ec.visibility_of_element_located((
                            By.ID, 'vm-details-state')))
                WebDriverWait(status_span, self.conf.wait_max_sec).until(
                    ec.visibility_of_element_located((
                        By.CLASS_NAME, 'fa-trash-o')))
            except:
                # Selenium can time-out by not realising the JS refresh
                url_save = self.get_url(fragment='activity')
                recent_destroy_vm = self.recently(
                    self.get_timeline_elements(
                        "vm.Instance.destroy", url_save))
                if not self.check_operation_result(
                        recent_destroy_vm, "a[href*='#activity']"):
                    logger.warning("Selenium cannot destroy "
                                   "the chosen %(id)s vm" % {
                                       'id': pk})
                    raise Exception('Cannot destroy the specified vm')
            self.driver.get('%s/dashboard/vm/%s/' % (self.conf.host, pk))
            try:
                WebDriverWait(self.driver, self.conf.wait_max_sec).until(
                    ec.visibility_of_element_located((
                        By.CSS_SELECTOR,
                        "span[data-status*='DESTROYED']")))
                logger.warning(
                    'Successfully deleted virtual machine: id - %(pk)s' % {
                        'pk': pk})
                return True
            except:
                return False
        except:
            logger.exception("Selenium can not destroy a VM")
            self.create_screenshot()
            raise Exception("Cannot destroy a VM")
