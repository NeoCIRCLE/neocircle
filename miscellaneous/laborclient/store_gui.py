#!/usr/bin/env python

import RSA
import gtk
import webkit
import gobject
import base64
import subprocess
import os

### Settings ###
KEY_DIR = "/home/tarokkk/Dropbox/python/"
KEY_FILE = KEY_DIR+"/id_rsa"
#Initalize keypair
private_key = RSA.generate(2048)
public_key = private_key.publickey()

#Saver private_key
f = open(KEY_FILE,'w')
f.write(private_key.exportKey())
f.close()
open_ssh_key = public_key.exportKey('OpenSSH')
os.chmod(KEY_FILE, 0600)

f = open(KEY_DIR+'/'+'id_rsa.pub','w')
f.write(open_ssh_key)
f.close()
pub_key_string = base64.b64encode(open_ssh_key)
#print pub_key_string


class Browser:
    neptun = ""
    host = ""
    def __init__(self):
        #Init window components
        gobject.threads_init()
        self.window = gtk.Window()
        self.window.connect("destroy", gtk.main_quit)
        self.window.set_title("IK CloudStore Login")

        #Init toolbar
        self.toolbar = gtk.Toolbar()

        #Init browser
        self.browser = webkit.WebView()
        #self.browser.connect('load-committed', self.load_committed_cb)
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
        #uri = frame.get_uri()
        #print uri
        #print web_view.get_title()
        return 

    def main(self):
        gtk.main()

if __name__ == "__main__":
    browser = Browser()
    browser.main()



