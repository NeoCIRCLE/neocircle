#!/usr/bin/env python

import gtk
import webkit
import gobject
import base64
import subprocess
import os

def keygen(length=1024):
    import os, base64
    from datetime import date
    from Crypto.PublicKey import RSA

    key = RSA.generate(length, os.urandom)
    try:
        pub = key.exportKey('OpenSSH')
        if not pub.startswith("ssh-"):
            raise ValueError(pub)
    except:
        ssh_rsa = '00000007' + base64.b16encode('ssh-rsa')
        exponent = '%x' % (key.e, )
        if len(exponent) % 2:
            exponent = '0' + exponent

        ssh_rsa += '%08x' % (len(exponent) / 2, )
        ssh_rsa += exponent

        modulus = '%x' % (key.n, )
        if len(modulus) % 2:
            modulus = '0' + modulus

        if modulus[0] in '89abcdef':
            modulus = '00' + modulus

        ssh_rsa += '%08x' % (len(modulus) / 2, )
        ssh_rsa += modulus

        pub = 'ssh-rsa %s' % (
            base64.b64encode(base64.b16decode(ssh_rsa.upper())), )
    return key.exportKey(), "%s %s" % (pub, "cloud-%s" % date.today())


### Settings ###
KEY_DIR = "/tmp/"
KEY_FILE = KEY_DIR+"/id_rsa"
#Initalize keypair
private_key, public_key = keygen(2048)

#Saver private_key
with open(KEY_FILE,'w') as f:
    f.write(private_key)
pub_key_string = base64.b64encode(public_key)


class Browser:
    neptun = ""
    host = ""
    def __init__(self):
        #Init window components
        gobject.threads_init()
        self.window = gtk.Window()
        self.window.connect("destroy", self.destroy)
        self.window.set_title("IK CloudStore Login")

        #Init toolbar
        self.toolbar = gtk.Toolbar()

        #Init browser
        self.browser = webkit.WebView()
        self.browser.connect('onload-event', self.load_committed_cb)
#        self.browser.open("http://10.9.1.86:8080")
        self.browser.open("https://cloud.ik.bme.hu/store/gui/")
        self.browser.connect("navigation-requested", self.on_navigation_requested)
        #self.browser.open("http://index.hu")
        
        #Sample button
        self.help_button = gtk.ToolButton(gtk.STOCK_HELP)
        self.help_button.connect("clicked",self.hello)
        self.store_button = gtk.ToolButton(gtk.STOCK_HOME)
        self.store_button.connect("clicked",self.store)
        
        #Connect things
        self.toolbar.add(self.store_button)
        self.toolbar.add(self.help_button)
        self.vbox = gtk.VBox(False, 0)
        self.vbox.pack_start(self.toolbar, False, True, 0)
        self.vbox.add(self.browser)
        self.window.add(self.vbox)
        #self.window.add(self.browser)
        self.window.show_all()

    def destroy(self, dummy):
        self.browser.execute_script("resetKey()")
        gtk.main_quit()

    def on_navigation_requested(self, view, frame, req, data=None):
        uri = req.get_uri()
        #print "On nav: " + uri
        scheme, rest = uri.split(':', 1)
        #print scheme
        try:
            self.neptun, rest = rest.split(':', 1)
            #print "Nep: "+neptun
            self.host, values = rest.split('?', 1)
            #print "Host: "+host
            #print "Values: "+values
        except:
            pass
        if scheme == 'login':
            self.browser.execute_script("postKey(\"%s\")" % pub_key_string)
            self.browser.execute_script("document.getElementById(\"login_button\").hidden=true ;")
            self.browser.execute_script("document.getElementById(\"logout_button\").hidden=false ;")
            self.browser.execute_script("document.getElementById(\"mount_button\").hidden=false ;")
            return True
        elif scheme == 'logout':
            self.browser.execute_script("resetKey()")
            self.browser.execute_script("document.getElementById(\"logout_button\").hidden=true ;")
            self.browser.execute_script("document.getElementById(\"login_button\").hidden=false ;")
            self.browser.execute_script("document.getElementById(\"mount_button\").hidden=true ;")
            return True
        elif scheme == "mount":
            self.mount_sshfs_folder(self.neptun,self.host)
            self.browser.execute_script("document.getElementById(\"mount_button\").hidden=true ;")
            self.browser.execute_script("document.getElementById(\"umount_button\").hidden=false ;")
            return True
        elif scheme == "umount":
            self.umount_sshfs_folder()
            self.browser.execute_script("document.getElementById(\"mount_button\").hidden=false ;")
            self.browser.execute_script("document.getElementById(\"umount_button\").hidden=true ;")
            return True
        else:
            return False
    def mount_sshfs_folder(self,neptun,host):
        with open(os.devnull, "w") as fnull:
            result = subprocess.call(['/usr/bin/sshfs', '-o', 'IdentityFile='+KEY_DIR+"/id_rsa", neptun+"@"+host+":home", "/home/tarokkk/sshfs"])
        #print result
    def umount_sshfs_folder(self):
        with open(os.devnull, "w") as fnull:
            result = subprocess.call(['/bin/fusermount', '-u', "/home/tarokkk/sshfs"])

    def hello(self, widget):
        self.browser.open("https://login.bme.hu/admin/")

    def store(self, widget):
        self.browser.open("https://cloud.ik.bme.hu/store/gui/")
    def load_committed_cb(self,web_view, frame):
        self.browser.execute_script('document.getElementsByTagName("a")[0].target="";')
        #uri = frame.get_uri()
        #print uri
        #print web_view.get_title()
        return 

    def main(self):
        gtk.main()

if __name__ == "__main__":
    browser = Browser()
    browser.main()



