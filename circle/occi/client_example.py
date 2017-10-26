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

import requests
import json
# import urllib3

# Mivel nincs a devenv-nek SSL tanusitvanya, ezert az urllib3 csomag minden
# keresnel InsecureRequestWarning-ot adna. Ezt elkeruljuk ugy, hogy
# kikapcsoljuk a figyelmezteteseket
# urllib3.disable_warnings()


def dumps(*args, **kwargs):
    try:
        return json.dumps(*args, **kwargs)
    except Exception as e:
        print(e)
    return {}


def loads(*args, **kwargs):
    try:
        return json.loads(*args, **kwargs)
    except Exception as e:
        print(e)
    return {}


# A szerver base url-je es a felhasznalo adatai
server = "https://localhost/"
username = "admin"
password = "retekretek"
loginData = {"username": username, "password": password}

# Csinalunk egy sessiont, hogy a cookie ami az auth-ert felelos
# automatikusan benne maradjon az osszes keresunkben
with requests.Session() as session:
    session.timeout = None
    headers = {"Content-Type": "application/json", "Referer": server}
    # Csrf-Token a bejelentkezeshez
    req = session.get(server + "occi/login/", headers=headers,
                      verify=False)
    print("csrf-token")
    print("----------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    # Bejelentkezes
    #   POST, DELETE, PUT keresek elott be kell allitani az X-CSRFToken
    #   header erteket az aktualis csrftoken-re, amely mindig benne van
    #   a cookie-ban
    headers["X-CSRFToken"] = req.cookies['csrftoken']
    req = session.post(server + "occi/login/", verify=False,
                       data=dumps(loginData), headers=headers)
    print("login")
    print("-----")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    headers["X-CSRFToken"] = req.cookies['csrftoken']
    req = session.get(server + "occi/token/", verify=False,
                      headers=headers)
    print("token")
    print("-----")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    token = req.json()["token"]

    req = session.get(server + "occi/test/?token=" + token, verify=False,
                      headers=headers)
    print("token-use")
    print("---------")
    print(server + "occi/test/?token=" + token)
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))

    req = session.get(server + "occi/test/?token=asdasdasd" + token, verify=False,
                      headers=headers)
    print("token-use")
    print("---------")
    print(server + "occi/test/?token=" + token)
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))

    exit()

    # storage creation wrong
    headers["X-CSRFToken"] = req.cookies['csrftoken']
    req = session.put(server + "occi/storage/100", verify=False,
                      data=dumps({}), headers=headers)
    print("storage_creation_wrong")
    print("---------------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    # query interface
    req = session.get(server + "occi/-/", headers=headers, verify=False)
    print("query-interface")
    print("---------------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    # osszes vm collectionkent
    req = session.get(server + "occi/compute/", headers=headers,
                      verify=False)
    print("compute-collection")
    print("------------------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    # az elso vm a listabol
    vmid = loads(req.text)["resources"][0]["id"]
    req = session.get(server + "occi/compute/" + vmid + "/",
                      headers=headers, verify=False)
    print("compute-" + str(vmid))
    print("------------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    # ha nem active, akkor azza tesszuk
    state = loads(req.text)["attributes"]["occi.compute.state"]
    action = "http://schemas.ogf.org/occi/infrastructure/compute/action#"
    if state != "active":
        try:
            headers["X-CSRFToken"] = req.cookies['csrftoken']
        except:
            pass
        req = session.post(server + "occi/compute/" + vmid + "/",
                           headers=headers, verify=False,
                           data=dumps({"action": action + "start"}))
        print("compute-" + str(vmid) + "-start")
        print("---------------")
        print("status_code: " + str(req.status_code))
        print
        print(dumps(loads(req.text), sort_keys=True,
                    indent=4, separators=(",", ": ")))
        print

#    # restart
#    try:
#        headers["X-CSRFToken"] = req.cookies['csrftoken']
#    except:
#        pass
    actionatrs = {"method": "cold"}
    actioninv = {"action": action + "restart", "attributes": actionatrs}
#    req = session.post(server + "occi/compute/" + vmid + "/",
#                       headers=headers, verify=False,
#                       data=dumps(actioninv))
#    print("compute-" + str(vmid) + "-restart")
#    print("-----------------")
#    print("status_code: " + str(req.status_code))
#    print
#    print(dumps(loads(req.text), sort_keys=True,
#                indent=4, separators=(",", ": ")))
#    print

    # stop
    try:
        headers["X-CSRFToken"] = req.cookies['csrftoken']
    except:
        pass
    actioninv["action"] = action + "stop"
    actioninv["attributes"]["method"] = "poweroff"
    req = session.post(server + "occi/compute/" + vmid + "/",
                       headers=headers, verify=False,
                       data=dumps(actioninv))
    print("compute-" + str(vmid) + "-stop")
    print("-----------------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    # renew action
    try:
        headers["X-CSRFToken"] = req.cookies["csrftoken"]
    except:
        pass
    actioninv["action"] = action + "renew"
    req = session.post(server + "occi/compute/" + vmid + "/",
                       headers=headers, verify=False,
                       data=dumps(actioninv))
    print("compute-" + str(vmid) + "-renew")
    print("-------------------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    # networkinterface add interface
    try:
        headers["X-CSRFToken"] = req.cookies["csrftoken"]
    except:
        pass
    req = session.put(server + "occi/networkinterface/compute" + vmid + "-network3/",
                      headers=headers, verify=False,
                      data=dumps({}))
    print("nif-creation")
    print("-------------------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    # networkinterface addport
    actionatrs = {"protocol": "tcp", "port": 1111}
    actioninv = {"action": "addport", "attributes": actionatrs}
    try:
        headers["X-CSRFToken"] = req.cookies["csrftoken"]
    except:
        pass
    req = session.post(server + "occi/networkinterface/compute" + vmid + "-network3/",
                       headers=headers, verify=False,
                       data=dumps(actioninv))
    print("networkinterface-addport")
    print("-------------------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    # networkinterface removeport
    actionatrs = {"protocol": "tcp", "port": 1111}
    actioninv = {"action": "removeport", "attributes": actionatrs}
    try:
        headers["X-CSRFToken"] = req.cookies["csrftoken"]
    except:
        pass
    req = session.post(server + "occi/networkinterface/compute" + vmid + "-network3/",
                       headers=headers, verify=False,
                       data=dumps(actioninv))
    print("networkinterface-addport")
    print("-------------------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

    # networkinterface remove interface
    try:
        headers["X-CSRFToken"] = req.cookies["csrftoken"]
    except:
        pass
    req = session.delete(server + "occi/networkinterface/compute" + vmid + "-network3/",
                         headers=headers, verify=False)
    print("nif-creation")
    print("-------------------")
    print("status_code: " + str(req.status_code))
    print
    print(dumps(loads(req.text), sort_keys=True,
                indent=4, separators=(",", ": ")))
    print

#
#    # vm krealas
#    try:
#        headers["X-CSRFToken"] = req.cookies["csrftoken"]
#    except:
#        pass
#    # a template mixinje benne kell legyen az adatokban
#    # az osszes template a query interfacen megjelenik mint mixin
#    # azok a mixinek templatek amik az os_tpl mixintol fuggnek
#    putdata = {"mixins": [
#        "http://circlecloud.org/occi/templates/os#os_template_1"],
#        "other_occi_compute_data": "may be provided"}
#    req = session.put(server + "occi/compute/1/",
#                      headers=headers, verify=False,
#                      data=dumps(putdata))
#    print("create_compute")
#    print("--------------")
#    print("status_code: " + str(req.status_code))
#    print
#    print(dumps(loads(req.text), sort_keys=True,
#                     indent=4, separators=(",", ": ")))
#    print
#
#    # vm torles
#    try:
#        headers["X-CSRFToken"] = req.cookies["csrftoken"]
#    except:
#        pass
#    vmid = loads(req.text)["id"]
#    req = session.delete(server + "occi/compute/" + vmid + "/",
#                         headers=headers, verify=False,
#                         data=dumps(putdata))
#    print("delete_compute")
#    print("--------------")
#    print("status_code: " + str(req.status_code))
#    print
#    print(dumps(loads(req.text), sort_keys=True,
#                     indent=4, separators=(",", ": ")))
#    print
#
#    try:
#        headers["X-CSRFToken"] = req.cookies["csrftoken"]
#    except:
#        pass
#    req = session.get(server + "occi/network/1/", headers=headers,
#                      verify=False)
#    print("storage")
#    print("-------")
#    print("status_code " + str(req.status_code))
#    print
#    print(dumps(loads(req.text), sort_keys=True,
#                     indent=4, separators=(",", ": ")))
#
#    try:
#        headers["X-CSRFToken"] = req.cookies["csrftoken"]
#    except:
#        pass
#    req = session.post(server + "occi/network/1/", headers=headers,
#                       verify=False, data=dumps({"action": "online"}))
#    print("storage")
#    print("-------")
#    print("status_code " + str(req.status_code))
#    print
#    print(dumps(loads(req.text), sort_keys=True,
#                     indent=4, separators=(",", ": ")))
#
#    try:
#        headers["X-CSRFToken"] = req.cookies["csrftoken"]
#    except:
#        pass
#    req = session.post(server + "occi/compute/96/", headers=headers,
#                       verify=False, data=dumps(
#                           {
#                               "attributes": {
#                                "occi.compute.memory": 0.250
#                               }
#                           }))
#    print("computerehelelel")
#    print("-------")
#    print("status_code " + str(req.status_code))
#    print
#    print(dumps(loads(req.text), sort_keys=True,
#                     indent=4, separators=(",", ": ")))
#
#    # Kijelentkezes
#    req = session.get(server + "occi/logout/", headers=headers,
#                      verify=False)
#    print("logout")
#    print("------")
#    print("status_code: " + str(req.status_code))
#    print
#    print(dumps(loads(req.text), sort_keys=True,
#                     indent=4, separators=(",", ": ")))
