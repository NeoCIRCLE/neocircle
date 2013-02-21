from celery import Celery, task
import subprocess
import time, re
import socket

BROKER_URL = 'amqp://nyuszi:teszt@localhost:5672/django'
IRC_CHANNEL = '/home/cloud/irc/irc.atw.hu/#ik/in'
try:
        from local_settings import *
except:
        pass

CELERY_CREATE_MISSING_QUEUES=True
celery = Celery('tasks', broker=BROKER_URL)


@task(name="firewall.tasks.reload_firewall_task")
def t(data4, data6):
    print "fw"
#    return
#    print "\n".join(data6['filter']) + "\n"
    process = subprocess.Popen(['/usr/bin/sudo', '/sbin/ip6tables-restore', '-c'], shell=False, stdin=subprocess.PIPE)
    process.communicate("\n".join(data6['filter']) + "\n")
    process = subprocess.Popen(['/usr/bin/sudo', '/sbin/iptables-restore', '-c'], shell=False, stdin=subprocess.PIPE)
    process.communicate("\n".join(data4['filter']) + "\n" + "\n".join(data4['nat']) + "\n")

@task(name="firewall.tasks.reload_dhcp_task")
def t(data):
    print "dhcp"
#    return
    with open('/tools/dhcp3/dhcpd.conf.generated', 'w') as f:
        f.write("\n".join(data)+"\n")
    subprocess.call(['sudo', '/etc/init.d/isc-dhcp-server', 'restart'], shell=False)

@task(name="firewall.tasks.reload_blacklist_task")
def t(data):
    print "blacklist"
    r = re.compile(r'^add blacklist ([0-9.]+)$')

    data_new = [ x['ipv4'] for x in data]
    data_old = []

    p = subprocess.Popen(['/usr/bin/sudo', '/usr/sbin/ipset', 'save', 'blacklist'], shell=False, stdout=subprocess.PIPE)
    for line in p.stdout:
        x = r.match(line.rstrip())
        if x:
            data_old.append(x.group(1))

    l_add = list(set(data_new).difference(set(data_old)))
    l_del = list(set(data_old).difference(set(data_new)))

    ipset = []
    ipset.append('create blacklist hash:ip family inet hashsize 4096 maxelem 65536')
    ipset = ipset + [ 'add blacklist %s' % x for x in l_add ]
    ipset = ipset + [ 'del blacklist %s' % x for x in l_del ]

    print "\n".join(ipset) + "\n"

    p = subprocess.Popen(['/usr/bin/sudo', '/usr/sbin/ipset', 'restore', '-exist'], shell=False, stdin=subprocess.PIPE)
    p.communicate("\n".join(ipset) + "\n")

    try:
        with open(IRC_CHANNEL, 'w') as f:
            for x in data:
                if x['ipv4'] in l_add:
                    f.write('%(ip)s(%(hostname)s) kibachva %(reason)s miatt\n' % { 'ip': x['ipv4'], 'reason': x['reason'], 'hostname': socket.gethostbyaddr(x['ipv4'])[0]})
    except:
        print "nem sikerult mircre irni"
        raise

