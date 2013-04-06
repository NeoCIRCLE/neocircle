#!/usr/bin/env python

import gtk
import webkit
import gobject
import base64
import os
import sys
import rdp
from multiprocessing import Process
import subprocess
import tempfile

class KeyGen:
    """Attributes:
    private_key
    public_key
    """

    def __init__(self):
        self.private_key, self.public_key = self.keygen(2048)
  
    def keygen(self,length=1024):
        """Generate Keypair for SSH
        (private_key, public_key)
        """
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




class Browser:
    version = "0.1"
    mounted = False
    neptun = ""
    host = ""
    private_key_file = ""
    public_key_b64 = ""
    params = {}
    def __init__(self):
        #Init window components
        gobject.threads_init()
        self.window = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
        #Register window events
        self.window.connect("destroy", self.destroy)


        #DEBUG
        self.window.set_decorated(True)
        self.window.set_title("IK CloudStore Login")
        self.window.set_default_size(1024,600)
        self.window.set_position(gtk.WIN_POS_CENTER)

        #Init browser
        self.webview = webkit.WebView()
        self.webview.connect('onload-event', self.load_committed_cb)
        self.webview.open("https://cloud.ik.bme.hu/store/gui/")
        self.webview.connect("navigation-requested", self.on_navigation_requested)
        settings = webkit.WebSettings()
        settings.set_property('user-agent', 'cloud-gui '+self.version)
        settings.set_property('enable-accelerated-compositing', True)
        settings.set_property("enable-default-context-menu", False)
        self.webview.set_settings(settings)

        #Connect things
        self.scrolledwindow = gtk.ScrolledWindow()
        self.scrolledwindow.add(self.webview)
        self.window.add(self.scrolledwindow)
        self.window.maximize()
        self.window.show_all()

    def init_keypair(self):
        keygen = KeyGen()
        private_key = keygen.private_key
        public_key = keygen.public_key

        #Saver private_key to KEY_FILE
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(private_key)
            self.private_key_file = f.name
        self.public_key_b64 =  base64.b64encode(public_key)
    
    def destroy(self, dummy):
        try:
            os.unlink(self.private_key_file)
        except:
            pass
        try:
            self.umount_sshfs_folder()
        except:
            pass
        gtk.main_quit()

    def on_navigation_requested(self, view, frame, req, data=None):
        uri = req.get_uri()
        if uri == "https://login.bme.hu/admin/":
            gobject.threads_init()
            window = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
            browser = webkit.WebView()
            browser.open(uri)
            window.add(browser)
            window.show_all()
            return True
        elif uri == "https://cloud.ik.bme.hu/logout/":
            self.umount_sshfs_folder()
        try:
            scheme, rest = uri.split(":", 1)
            if scheme == "nx" or scheme == "rdp" or scheme == "sshterm":
                subprocess.Popen(["/usr/local/bin/rdp",uri])
                return True
            elif scheme == "cloudfile":
                file_path = os.path.normpath(rest)
                subprocess.call(["xdg-open","file://"+self.folder+file_path])
                return True
            else:
                return False
        except:
            False
    def mount_sshfs_folder(self):
        self.folder = os.path.expanduser("~/sshfs")
        neptun = self.params["neptun"]
        host = self.params["host"]
        try:
            os.makedirs(self.folder)
        except:
            pass
        result = subprocess.call(['/usr/bin/sshfs', '-o', 'IdentityFile='+self.private_key_file+',StrictHostKeyChecking=no', neptun+"@"+host+":home", self.folder])
        #print result
    def umount_sshfs_folder(self):
        try:
            result = subprocess.call(['/bin/fusermount', '-u', self.folder])
        except:
            pass
    def post_key(self,key = None):
        if key != None:
            js = '''
            $.post("/store/gui/", { "KEY" : "%(key)s" }, 
                                function (respond) {
                                    window.location = respond;
                                    }
                                )
                             .error(function (respond) { alert(JSON.stringify(respond)); });
                           ''' % { "key" : key }
        else:
            js = '''
            $.post("/store/gui/", "", 
                                function (respond) {
                                    window.alert(respond);
                                    }
                                )
                             .error(function (respond) { alert(JSON.stringify(respond)); });
                           '''
        self.webview.execute_script(js)
        
    def load_committed_cb(self,web_view, frame):
        uri = frame.get_uri()
        print uri
        try:
            self.webview.execute_script('document.getElementsByTagName("a")[0].target="";')
        except:
            pass
        ### Send keys via JavaScript ###
        if uri == "https://cloud.ik.bme.hu/store/gui/":
            self.init_keypair()
            ### JS
            self.post_key(self.public_key_b64)
            ### Parse values and do mounting ###
        elif uri.startswith("https://cloud.ik.bme.hu/home/?"):
            if self.mounted != True:
                try:
                    uri, params = uri.split('?', 1)
                    values = params.split('&')
                    for p in values:
                        key, value = p.split('=',1)
                        self.params[key] = value
                    try:
                        self.mount_sshfs_folder()
                    except Exception as e:
                        print e
                    self.mounted = True
                except:
                    pass 
                finally:
                    os.unlink(self.private_key_file)
        return True
    def main(self):
        gtk.main()
    
if __name__ == "__main__":
    browser = Browser()
    browser.main()

