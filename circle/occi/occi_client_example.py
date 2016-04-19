import requests
from requests.exceptions import ConnectionError
import json
import urllib3

# Mivel nincs a devenv-nek SSL tanusitvanya, ezert az urllib3 csomag minden keresnel
# InsecureRequestWarning-ot adna. Ezt elkeruljuk ugy, hogy kikapcsoljuk a
# figyelmezteteseket
# urllib3.disable_warnings()

# A szerver base url-je es a felhasznalo adatai
server = "https://vm.ik.bme.hu:15766/"
username = "admin"
password = "retekretek"
loginData = {"username": username, "password": password}

# Csinalunk egy sessiont, hogy a cookie ami az auth-ert felelos automatikusan benne
# maradjon az osszes keresunkben
with requests.Session() as session:
    headers = {"Content-Type": "application/json", "Referer" : server}
    try:
        # Csrf-Token a bejelentkezeshez
        req = session.get(server + "occi/login/", headers=headers, verify=False)
        print("csrf-token")
        print("----------")
        print("status_code: " + str(req.status_code))
        print(json.loads(req.text)["result"])
        print

        # Bejelentkezes
        #   POST, DELETE, PUT keresek elott be kell allitani az X-CSRFToken header
        #   erteket az aktualis csrftoken-re, amely mindig benne van a cookie-ban
        headers["X-CSRFToken"] = req.cookies['csrftoken']
        req = session.post(server + "occi/login/", data=json.dumps(loginData),
            headers=headers, verify=False)
        print("login")
        print("-----")
        print("status_code: " + str(req.status_code))
        if req.status_code == 200:
            print(json.loads(req.text)["result"])
        else:
            print(json.loads(req.text)["result"])
            errors = json.loads(req.text)["errors"]
            for error in errors:
                print(error)
        print

        # Gep ebresztes teszt (meg nem OCCI)
        req = session.get(server + "occi/wakeup/", headers=headers, verify=False)
        print("wakeup")
        print("------")
        print("status_code: " + str(req.status_code))
        print(req.text)
        print

        # Gep altatas teszt (meg nem OCCI)
        req = session.get(server + "occi/sleep/", headers=headers, verify=False)
        print("sleep")
        print("-----")
        print("status_code: " + str(req.status_code))
        print(req.text)
        print

        # Kijelentkezes
        req = session.get(server + "occi/logout/", headers=headers, verify=False)
        print("logout")
        print("------")
        print("status_code: " + str(req.status_code))
        print(json.loads(req.text)["result"])
    except ConnectionError as e:
        print(e)
