#!/usr/bin/env python

import subprocess
from celery import Celery, task
import time, re
import socket
import sys
import tempfile, os, stat, re, base64, struct, logging
from celery.contrib import rdb


BROKER_URL = os.environ['DJANGO_BROKER_URL']
try:
    from local_settings import *
except:
    pass
celery = Celery('tasks', broker=BROKER_URL, backend=BROKER_URL)
celery.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600,
)

def update_vm(one_id, template):
    out = ""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        os.chmod(f.name, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        tpl = u'''
            <COMPUTE>
            <ID>%(id)d</ID>
                %(template)s
            </COMPUTE>''' % {
                    "id": one_id,
                    "template": template
        }
        f.write(tpl)
        f.close()
        proc = subprocess.Popen(["/opt/occi.sh", "compute", "update",
            f.name], stdout=subprocess.PIPE)
        try:
            (out, err) = proc.communicate()
        except:
            pass
        os.unlink(f.name)


@task(name="one.tasks.CreateInstanceTask")
def t(name, instance_type, disk_id, network_id, ctx):
    out = ''
    f2 = tempfile.NamedTemporaryFile(delete=False)
    f2.close()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        os.chmod(f.name, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        tpl = u"""
                <COMPUTE>
                    <NAME>%(name)s</NAME>
                    <INSTANCE_TYPE href="http://www.opennebula.org/instance_type/%(instance)s"/>
                    <DISK>
                        <STORAGE href="http://www.opennebula.org/storage/%(disk)d"/>
                    </DISK>
                    <NIC>
                        <NETWORK href="http://www.opennebula.org/network/%(net)d"/>
                    </NIC>
                    <CONTEXT>
                        %(context)s
                    </CONTEXT>
                </COMPUTE>""" % {
                        "name": name,
                        "instance": instance_type,
                        "disk": disk_id,
                        "net": network_id,
                        "context": ctx,
                }
        f.write(tpl)
        f.close()
        proc = subprocess.Popen(["/opt/occi.sh compute creatE %s > %s" %
                ( f.name, f2.name )], shell=True)
        try:
            proc.communicate()
        except:
            pass
        with open(f2.name, 'r') as f3:
            out = f3.read()
        os.unlink(f.name)
        os.unlink(f2.name)

    from xml.dom.minidom import parse, parseString
    try:
        x = parseString(out)
        return {
            'one_id': int(x.getElementsByTagName("ID")[0].childNodes[0].nodeValue),
            'interfaces': [
                {
                    'ip': x.getElementsByTagName("IP")[0].childNodes[0].nodeValue,
                    'mac': x.getElementsByTagName("MAC")[0].childNodes[0].nodeValue,
                },
            ],
        }
    except:
        pass

@task(name="one.tasks.ChangeInstanceStateTask")
def t(one_id, new_state):
    update_vm(one_id, '<STATE>%s</STATE>' % (new_state, ))

@task(name="one.tasks.SaveAsTask")
def t(one_id, new_img):
    update_vm(one_id, '<DISK id="0"><SAVE_AS name="%s"/></DISK>' % new_img)

@task(name="one.tasks.UpdateDiskTask")
def t():
    f = tempfile.NamedTemporaryFile(delete=False)
    f.close()
    out=''
    proc = subprocess.Popen(["/opt/occi.sh storage list > %s" % f.name],
            shell=True)
    try:
        (out, err) = proc.communicate()
    except:
        pass
    from xml.dom.minidom import parse, parseString
    try:
        with open(f.name, 'r') as f2:
            out = f2.read()
        x = parseString(out)
        return [ {
                'id': int(d.getAttributeNode('href').nodeValue.split('/')[-1]),
                'name': d.getAttributeNode('name').nodeValue,
            } for d in x.getElementsByTagName("STORAGE")
        ]
    except:
        pass
    os.unlink(f)

@task(name="one.tasks.UpdateNetworkTask")
def t():
    f = tempfile.NamedTemporaryFile(delete=False)
    f.close()
    out=''
    proc = subprocess.Popen(["/opt/occi.sh network list > %s" % f.name],
            shell=True)
    try:
        (out, err) = proc.communicate()
    except:
        pass
    from xml.dom.minidom import parse, parseString
    try:
        with open(f.name, 'r') as f2:
            out = f2.read()
        x = parseString(out)
        return [ {
                'id': int(d.getAttributeNode('href').nodeValue.split('/')[-1]),
                'name': d.getAttributeNode('name').nodeValue,
            } for d in x.getElementsByTagName("NETWORK")
        ]
    except:
        pass
    os.unlink(f)

@task(name="one.tasks.DeleteInstanceTask")
def t(one_id):
    proc = subprocess.Popen(["/opt/occi.sh", "compute", "delete",
            "%d" % one_id], stdout=subprocess.PIPE)
    try:
        (out, err) = proc.communicate()
    except:
        pass

@task(name="one.tasks.GetInstanceStateTask")
def t(one_id):
    update_state(one_id)

def update_state(one_id):
    """Get and update VM state from OpenNebula."""
    proc = subprocess.Popen(["/opt/occi.sh", "compute", "show",
            "%d" % one_id], stdout=subprocess.PIPE)
    (out, err) = proc.communicate()
    state = 'UNKNOWN'
    try:
        if(len(sys.argv) == 3 and sys.argv[2] == 'UNKNOWN'):
            raise Exception(':(')
        from xml.dom.minidom import parse, parseString
        x = parseString(out)
        state = x.getElementsByTagName("STATE")[0].childNodes[0].nodeValue
    except:
        state = 'UNKNOWN'

    print state
    celery.send_task('one.tasks.UpdateInstanceStateTask', [one_id, state],
            queue='local')

if __name__ == "__main__":
    update_state(int(sys.argv[1]))

