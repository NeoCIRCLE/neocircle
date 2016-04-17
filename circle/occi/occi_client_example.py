import requests
from requests.exceptions import ConnectionError
import json
import urllib3

# Mivel nincs a devenv-nek SSL tanusitvanya, ezert az urllib3 csomag minden keresnel
# InsecureRequestWarning-ot adna. Ezt elkeruljuk ugy, hogy kikapcsoljuk a
# figyelmezteteseket
# urllib3.disable_warnings()

# A szerver base url-je es a felhasznalo adatai
server = "https://vm.ik.bme.hu:15766/occi/"
username = "admin"
password = "retekretek"
loginData = {"username": username, "password": password}

# Csinalunk egy sessiont, hogy a cookie ami az auth-ert felelos automatikusan benne
# maradjon az osszes keresunkben
with requests.Session() as session:
    try:
        # Bejelentkezes
        headers = {"Content-Type": "application/json"}
        req = session.post(server + "login/", data=json.dumps(loginData),
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
        req = session.get(server + "wakeup/", verify=False)
        print("wakeup")
        print("------")
        print("status_code: " + str(req.status_code))
        print(req.text)
        print

        # Gep altatas teszt (meg nem OCCI)
        req = session.get(server + "sleep/", verify=False)
        print("sleep")
        print("-----")
        print("status_code: " + str(req.status_code))
        print(req.text)
        print

        # Kijelentkezes
        req = session.get(server + "logout/", verify=False)
        print("logout")
        print("------")
        print("status_code: " + str(req.status_code))
        print(json.loads(req.text)["result"])
    except ConnectionError as e:
        print(e)
