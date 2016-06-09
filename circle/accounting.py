#!/usr/env/bin python
# coding=utf-8
# vim: set fileencoding=utf-8

###########################################################
#
# Accounting modul for Circle cloud.
#
# Created by Csatlós Tamás Péter
#
#
############################################################

from django.contrib.auth.models import User
from django.db.models import Q

from datetime import datetime
from datetime import timedelta

from operator import itemgetter

import json

ACC_DATE_FORMAT = '%Y.%m.%d %H:%M:%S.%f'  # const to the dates
ACC_FILE_NAME = 'acc_out.json'

# Collect every data for accounting
class ResourceCollector():

    name = 'resource_collector'

    def __init__(self, delta_time=7, start=None, end=None):
        self.activities = dict()
        self.is_collection_successfull = False

        if start is None:
            if delta_time is None or delta_time < 1:
                raise Exception('End date is missing!')

            if end is None:
                temp_date = datetime.now()
                self.end_date = datetime(
                    temp_date.year,
                    temp_date.month,
                    temp_date.day,
                    temp_date.hour + (23 - temp_date.hour),
                    temp_date.minute + (59 - temp_date.minute),
                    temp_date.second + (59 - temp_date.second)
                )
            else:
                assert isinstance(end, datetime)
                self.end_date = end
            self.dt = delta_time
            self.start_date = self.end_date - timedelta(
                days=delta_time,
                hours=self.end_date.hour,
                minutes=self.end_date.minute,
                seconds=self.end_date.second
            )
        else:
            if end is None:
                raise Exception('End date is missing!')
            assert isinstance(start, datetime)
            assert isinstance(end, datetime)
            delta_time = end - start
            if delta_time.days < 1:
                raise Exception('Least one day time interval!')
            self.start_date = start
            self.end_date = end
            self.dt = delta_time.days

    def get_time_interval(self):
        return {'start': self.start_date, 'end':  self.end_date}

    # Collect every user's data.
    def collect_data(self):
        try:
            # get every user from the db (db conn. #1)
            users = User.objects.all()
            for user in users:
                temp_list = self.collect_user_data(
                    self.start_date,
                    self.end_date,
                    user
                )

                self.activities[user.get_username()] = temp_list

            self.is_collection_successfull = True
            return True
        except Exception as ex:
            print ex.message
            return False

    def write_data(self, filename=ACC_FILE_NAME):
        try:
            if self.is_collection_successfull:
                with open(filename, 'w') as file:
                    json.dump(
                        self.activities,
                        file,
                        indent=4,
                        separators=(',', ': ')
                    )
                return True
            else:
                return False
        except Exception:
            return False

    def write_given_resource_data(self, resources, filename):
        try:
            if (not resources == {} or not filename == ''):
                with open(filename, 'w') as file:
                    json.dump(
                        resources,
                        file,
                        indent=4,
                        separators=(',', ': ')
                    )
                return True
            else:
                return False
        except Exception:
            return False

    def collect_user_data(self, start_time, end_time, user):
        if user is None:
            return None

        temp_list = []
        usr_acts = user.instanceactivity_set.filter(
            Q(started__range=(start_time, end_time)),
            Q(finished__range=(start_time, end_time)),
            Q(succeeded__exact=True),
            Q(activity_code__exact='vm.Instance.deploy') |
            Q(activity_code__exact='vm.Instance.create') |
            Q(activity_code__exact='vm.Instance.destroy') |
            Q(activity_code__exact='vm.Instance.sleep') |
            Q(activity_code__exact='vm.Instance.wake_up') |
            Q(activity_code__exact='vm.Instance.sleep') |
            Q(activity_code__exact='vm.Instance.renew') |
            Q(activity_code__startswith='vm.Instance.shut')
            ).order_by('instance_id', 'started').values(
                'id',
                'instance_id',
                'user_id',
                'started',
                'finished',
                'activity_code'
            ).all()

        for act in usr_acts:
            useful_data_chunk = dict(
                id=act['id'],  # Activity ID
                activity_code=act['activity_code'],  # What?
                started=act['started'].strftime(ACC_DATE_FORMAT),  # When?
                finished=act['finished'].strftime(ACC_DATE_FORMAT),
                user_id=act['user_id'],  # Who did that?
                instance_id=act['instance_id']
            )

            instances = user.instance_set.filter(
                Q(id__exact=act['instance_id']),
                Q(owner_id__exact=act['user_id'])
            ).all()

            if instances:
                ins = instances[0]

                useful_data_chunk['ram'] = ins.ram_size
                useful_data_chunk['cores'] = ins.num_cores
                useful_data_chunk['core_prio'] = ins.priority
                useful_data_chunk['disks'] = []

                # Get all disks
                ins_disks = ins.disks.all().values('size', 'id')

                for disk in ins_disks:
                    useful_data_chunk['disks'].append(
                        {'size': disk['size'], 'id': disk['id']}
                    )
            else:
                # Sharaed machine
                useful_data_chunk['ram'] = -1
                useful_data_chunk['cores'] = -1
                useful_data_chunk['core_prio'] = -1
                useful_data_chunk['is_running'] = None
                useful_data_chunk['disks'] = []

            temp_list.append(useful_data_chunk)
        return temp_list

    def get_one_users_data(self, user=u'admin'):
        if self.is_collection_successfull:
            return self.activities[user]
        else:
            return None

    def get_data(self):
        if self.is_collection_successfull:
            return self.activities
        else:
            return None

    def is_successfull(self):
        return self.is_collection_successfull

# Makes report about the resource usage
class ReportMaker():

    name = 'report_maker'

    # create report maker object
    # start, end has to be datetime objects
    def __init__(self, start, end, collected_data=None):
        try:
            self.data = None
            self.is_data_avaiable = False

            if collected_data is None:
                self.read_data()
            else:
                self.data = collected_data
            
            assert isinstance(start, datetime)
            assert isinstance(end, datetime)

            self.start_date = start
            self.end_date = end
            self.is_data_avaiable = True

        except Exception:
            self.data = None
            self.is_data_avaiable = False

    def set_data(self, new_data):
        self.data = new_data

    def get_time_interval(self):
        return {'start': self.start_date, 'end':  self.end_date}

    def read_data(self, filename=ACC_FILE_NAME):
        try:
            self.is_data_avaiable = False
            with open(filename, 'r') as file:
                self.data = json.load(file)
            self.is_data_avaiable = True
            return True
        except Exception:
            self.is_data_avaiable = False
            return False

    def make_report_about_everyone(self):
        if self.is_data_avaiable:
            for user in self.data.keys():
                file_name = user + '.txt'

                if self.data[user] == []:
                    users_bill = None
                else:
                    users_bill = self.billing(user, self.data[user])

                # start and end is datetime, not serializable
                interval = {'start': self.start_date.strftime(ACC_DATE_FORMAT),
                            'end': self.end_date.strftime(ACC_DATE_FORMAT)}

                with open(file_name, 'w') as file:
                    json.dump(interval, file)
                    json.dump(
                        users_bill,
                        file,
                        indent=4,
                        separators=(',', ': ')
                    )

            return True

        raise Exception('Error occured while making report about everyone!')

    def billing(self, user, activity_list):
        # the usage of the resources
        bill = dict()

        # every machine ID which used by the user
        machines = self.get_machines(activity_list)

        # every activity for one machine
        activity_by_machines = self.get_acts(activity_list)

        # iterate over the user's machines
        for ins in machines:

            run_state = {
                'started': '',
                'ended': '',
                'renewed_times': 0,
                'created': False
            }
            total_usage = {
                'total_run_time': 0,
                'total_used_cores': 0,
                'total_used_ram': 0,
                'total_used_disk': 0,
                'total_cost': 0
            }
            bill[ins] = []

            for act in activity_by_machines[ins]:
                # calculating usage
                if 'create' in act['activity_code']:
                    run_state['created'] = True
                elif ('deploy' in act['activity_code'] or
                        'wake_up' in act['activity_code']):
                    run_state['started'] = act['finished']

                elif 'renew' in act['activity_code']:
                    run_state['renewed_times'] += 1

                elif ('sleep' in act['activity_code'] or
                        'shut' in act['activity_code'] or
                        'destroy' in act['activity_code']):
                    run_state['ended'] = act['started']  # end of running

                    # stopped, but did not start during T
                    # so the start of the runing is the begining of the T
                    if run_state['started'] == '':
                        if run_state['created']:
                            # létrejött, de nem tudott futni (create-->destroy)
                            break
                        else:
                            run_state['started'] = self.start_date.strftime(
                                ACC_DATE_FORMAT
                            )  # datetime -> str
                            
                    bill[ins].append(
                        self.construct_bill(
                            act=act,
                            begin=run_state['started'],
                            end=run_state['ended'],
                            rt=run_state['renewed_times']
                        )
                    )

                    # reset the helper dictionary
                    run_state = {
                        'started': '',
                        'ended': '',
                        'renewed_times': 0,
                        'created': False
                    }
                    
                # end of activity loop

            # T alatt elkezdődött, de nem befejezett futás
            if (run_state['ended'] == '' and
                    not run_state['started'] == ''):
                run_state['ended'] = self.end_date.strftime(ACC_DATE_FORMAT)
                
                bill[ins].append(
                    self.construct_bill(
                        act=act,
                        begin=run_state['started'],
                        end=run_state['ended'],
                        rt=run_state['renewed_times']
                    )
                )

            # calculate total used time, and resources
            for act in bill[ins]:
                total_usage['total_used_cores'] += act['used_cores']
                total_usage['total_used_ram'] += act['used_ram']
                
                for disk in act['disks']:
                    total_usage['total_used_disk'] += disk['size']

                if total_usage['total_run_time'] == 0:
                    total_usage['total_run_time'] = act['run_time']
                else:
                    total_usage['total_run_time'] += act['run_time']

                act['run_time'] = str(act['run_time'])  # deltatime -> str

            total_usage['total_run_time'] = str(  # deltatime -> str
                total_usage['total_run_time']
            )
            bill[ins].append(total_usage)

        return bill

    def construct_bill(self, act, begin, end, rt):
        temp_dict = {
            'run_time':
                datetime.strptime(end, ACC_DATE_FORMAT) -
                datetime.strptime(begin, ACC_DATE_FORMAT),  # deltatime
            'used_ram': act['ram'],
            'used_cores': act['cores'],
            'cost': 0,
            'cores_priority': act['core_prio'],
            'renewed': rt,
            'disks': act['disks'],
            'started': begin,  # str
            'finished': end    # str as well
        }
        return temp_dict

    def get_machines(self, activity_list):
        if len(activity_list) == 0:
            return None

        machines = set()
        for act in activity_list:
            machines.add(act['instance_id'])
        return list(machines)

    def get_acts(self, activity_list):
        if len(activity_list) == 0:
            return None

        machines_acts = {activity_list[0]['instance_id']: []}
        
        for act in activity_list:
            if act['instance_id'] in machines_acts.keys():
                machines_acts[act['instance_id']].append(act)

                machines_acts[act['instance_id']] = sorted(
                    machines_acts[act['instance_id']],
                    key=itemgetter('started')
                )
            else:
                machines_acts[act['instance_id']] = []
                machines_acts[act['instance_id']].append(act)

        return machines_acts

# Wrapper class in order to use accounting easily
class Accounter():

    name = 'accounter'
    
    def billing_everyone(self, t0, t1):
        try:
            collector = ResourceCollector(start=t0, end=t1)
            if collector.collect_data():
                maker = ReportMaker(t0, t1, collector.activities)
                if maker.make_report_about_everyone():
                    return True
                raise Exception('Billing failed!')                
            raise Exception('Data collection failed!')
        except Exception as e:
            print e
            return None
    
    def billing_user(self, user, t0, t1):
        try:
            user_data_list = ResourceCollector.
                                collect_user_data(t0, t1, user)
            if not user_data_list is None:
                maker = ReportMaker(t0,t1)
                bill = maker.billing(user,
                                        user_data_list)
                return bill
        except Exception as e:
            print e
            return None
    