#!/usr/bin/python

# TODO File permission checks

from bottle import route, run, request, static_file, abort, redirect, app, response
import json, os, shutil
import uuid
import subprocess
import ConfigParser
from pwd import getpwnam
import multiprocessing

# Get configuration file
config = ConfigParser.ConfigParser()
config.read('/opt/webadmin/cloud/miscellaneous/store-server/store.config')


ROOT_WWW_FOLDER = config.get('store', 'root_www_folder')
ROOT_BIN_FOLDER = config.get('store', 'root_bin_folder')
SITE_URL = config.get('store', 'site_url')
USER_MANAGER = config.get('store', 'user_manager')
# Standalone server
SITE_HOST = config.get('store', 'site_host')
SITE_PORT = config.get('store', 'site_port')
# Temporary dir for tar.gz
TEMP_DIR = config.get('store', 'temp_dir')
#Redirect
try:
    REDIRECT_URL = config.get('store', 'redirect_url')
except:
    REDIRECT_URL = "https://cloud.ik.bme.hu"
#ForceSSL
try:
    FORCE_SSL = config.get('store', 'force_ssl') == "True"
except:
    FORCE_SSL = False


def force_ssl(original_function):
    def new_function(*args, **kwargs):
        if FORCE_SSL:
            ssl = request.environ.get('SSL_CLIENT_VERIFY', 'NONE')
            if ssl != "SUCCESS":
                abort(403, "Forbidden requests. This site need SSL verification! SSL status: "+ssl)
            else:
                return original_function(*args, **kwargs)
        else:
            return original_function(*args, **kwargs)
    return new_function

@route('/')
@force_ssl
def index():
    response = "NONE"
    try:
        response = request.environ.get('SSL_CLIENT_VERIFY', 'NONE')
    except:
        pass
    return "It works! SSL: "+response

# @route('/<neptun:re:[a-zA-Z0-9]{6}>', method='GET')
@route('/<neptun>', method='GET')
@force_ssl
def neptun_GET(neptun):
    home_path = '/home/'+neptun+'/home'
    if os.path.exists(home_path) != True:
        abort(401, 'The requested user does not exist!')
    else:
        statistics=get_quota(neptun)
        return { 'Used' : statistics[0], 'Soft' : statistics[1], 'Hard' : statistics[2]}

COMMANDS = {}

@route('/<neptun>', method='POST')
@force_ssl
def neptun_POST(neptun):
    # Check if user avaiable (home folder ready)
    home_path = '/home/'+neptun+'/home'
    if os.path.exists(home_path) != True:
        abort(401, 'The requested user does not exist!')
    else:
        try:
            return COMMANDS[request.json['CMD']](request, neptun, home_path)
        except KeyError:
            abort(400, "Command not found!")


# LISTING
def cmd_list(request, neptun, home_path):
    list_path = home_path+request.json['PATH']
    if os.path.exists(list_path) != True:
        abort(404, "Path not found!")
    else:
        return list_directory(home_path, list_path)
COMMANDS['LIST'] = cmd_list

# DOWNLOAD LINK GENERATOR
def cmd_download(request, neptun, home_path):
    dl_path = home_path+'/'+request.json['PATH']
    dl_path = os.path.realpath(dl_path)
    if not dl_path.startswith(home_path):
        abort(400, 'Invalid download path.')
    dl_hash = str(uuid.uuid4())
    dl_pub = os.path.join(ROOT_WWW_FOLDER, dl_hash)
    if os.path.isfile(dl_path):
        os.symlink(dl_path, dl_pub)
        return json.dumps({'LINK' : SITE_URL+'/dl/'+dl_hash})
    else:
        shutil.make_archive(dl_pub, 'zip', dl_path)
        return json.dumps({'LINK' : SITE_URL+'/dl/'+dl_hash+'.zip'})
COMMANDS['DOWNLOAD'] = cmd_download

# UPLOAD
def cmd_upload(request, neptun, home_path):
    up_path = home_path+'/'+request.json['PATH']
    up_path = os.path.realpath(up_path)
    if not up_path.startswith(home_path):
        abort(400, 'Invalid upload path.')
    if os.path.exists(up_path) == True and os.path.isdir(up_path):
        up_hash = str(uuid.uuid4())
        link = ROOT_WWW_FOLDER + '/' + up_hash
        os.symlink(up_path, link)
        passwd = getpwnam(neptun)
        os.lchown(link, passwd.pw_uid, passwd.pw_gid)
        return json.dumps({ 'LINK' : SITE_URL+'/ul/'+up_hash})
    else:
        abort(400, 'Upload directory not exists!')
COMMANDS['UPLOAD'] = cmd_upload

# MOVE
def cmd_move(request, neptun, home_path):
    src_path = home_path+'/'+request.json['SOURCE']
    dst_path = home_path+'/'+request.json['DESTINATION']
    src_path = os.path.realpath(src_path)
    dst_path = os.path.realpath(dst_path)
    if not src_path.startswith(home_path):
        abort(400, 'Invalid source path.')
    if not dst_path.startswith(home_path):
        abort(400, 'Invalid destination path.')
    if os.path.exists(src_path) == True and os.path.exists(dst_path) == True and os.path.isdir(dst_path) == True:
        shutil.move(src_path, dst_path)
        return
    else:
    # TODO
        abort(400, "Can not move the file.")
COMMANDS['MOVE'] = cmd_move

# RENAME
def cmd_rename(request, neptun, home_path):
    src_path = home_path+'/'+request.json['PATH']
    src_path = os.path.realpath(src_path)
    if not src_path.startswith(home_path):
        abort(400, 'Invalid source path.')
    dst_path = os.path.dirname(src_path)+'/'+request.json['NEW_NAME']
    if os.path.exists(src_path) == True:
        os.rename(src_path, dst_path)
    else:
        abort(404, "File or Folder not found!")
COMMANDS['RENAME'] = cmd_rename

# NEW FOLDER
def cmd_new_folder(request, username, home_path):
    dir_path = home_path+'/'+request.json['PATH']
    dir_path = os.path.realpath(dir_path)
    if not dir_path.startswith(home_path):
        abort(400, 'Invalid directory path.')
    if os.path.exists(dir_path) == True:
        abort(400, "Directory already exist!")
    else:
        os.mkdir(dir_path, 0755)
        os.chown(dir_path, getpwnam(username).pw_uid, getpwnam(username).pw_gid)
COMMANDS['NEW_FOLDER'] = cmd_new_folder

# REMOVE
def cmd_remove(request, neptun, home_path):
    remove_path = home_path+'/'+request.json['PATH']
    remove_path = os.path.realpath(remove_path)
    if not remove_path.startswith(home_path):
        abort(400, 'Invalid path.')
    if os.path.exists(remove_path) != True:
        abort(404, "Path not found!")
    else:
        if os.path.isdir(remove_path) == True:
            shutil.rmtree(remove_path)
            return
        else:
            os.remove(remove_path)
            return
COMMANDS['REMOVE'] = cmd_remove

def cmd_toplist(request, neptun, home_path):
    d = []
    try:
        top_dir = os.path.normpath(os.path.join(home_path, "../.top"))
        d = [file_dict(os.readlink(os.path.join(top_dir, f)), home_path)
                for f in os.listdir(top_dir)]
    except:
        pass
    return json.dumps(sorted(d, key=lambda f: f['MTIME']))
COMMANDS['TOPLIST'] = cmd_toplist

@route('/set/<neptun>', method='POST')
@force_ssl
def set_keys(neptun):
    key_list = []
    smb_password = ''
    try:
        smbpasswd = request.json['SMBPASSWD']
        for key in request.json['KEYS']:
            key_list.append(key)
    except:
        abort(400, 'Wrong syntax!')
    result = subprocess.call([ROOT_BIN_FOLDER+'/'+USER_MANAGER, 'set', neptun, smbpasswd])
    if result == 0:
        updateSSHAuthorizedKeys(neptun, key_list)
        return
    elif result == 2:
        abort(403, 'User does not exist!')
@route('/quota/<neptun>', method='POST')
@force_ssl
def set_quota(neptun):
    try:
        quota = request.json['QUOTA']
    except:
        abort(400, 'Wrong syntax!')
    result = subprocess.call([ROOT_BIN_FOLDER+'/'+USER_MANAGER, 'setquota', neptun, str(quota), hard_quota(quota)])
    if result == 0:
        return
    elif result == 2:
        abort(403, 'User does not exist!')


@route('/new/<neptun>', method='POST')
@force_ssl
def new_user(neptun):
    key_list = []
    smbpasswd = ''
    quota = ''
    try:
        smbpasswd = request.json['SMBPASSWD']
        quota = request.json['QUOTA']
    except:
        print "Invalid syntax"
        abort(400, 'Invalid syntax')
    # Call user creator script
    result = subprocess.call([ROOT_BIN_FOLDER+'/'+USER_MANAGER, 'add', neptun, smbpasswd, str(quota), hard_quota(quota)])
    print "add "+neptun+" "+smbpasswd+" "+str(quota)+" "+hard_quota(quota)
    if result == 0:
        try:
            for key in request.json['KEYS']:
                key_list.append(key)
            updateSSHAuthorizedKeys(neptun, key_list)
        except:
            print "SSH error"
            abort(400, 'SSH')
        return
    elif result == 2:
        abort(403, 'User already exist!')
    else:
        print "Error"
        abort(400, 'An error occured!')



# Static file
@route('/dl/<hash_num>', method='GET')
def dl_hash(hash_num):
    hash_path = ROOT_WWW_FOLDER
    if os.path.exists(hash_path+'/'+hash_num) != True:
        abort(404, "File not found!")
    else:
        filename = os.path.basename(os.path.realpath(hash_path+'/'+hash_num))
        return static_file(hash_num, root=hash_path, download=filename)

@route('/ul/<hash_num>', method='OPTIONS')
def upload_allow(hash_num):
    response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    response.set_header('Access-Control-Allow-Headers', 'Content-Type, Content-Range, Content-Disposition, Content-Description')
    return 'ok'


def _upload_save(uid, gid, input, path):
    os.setegid(gid)
    os.seteuid(uid)
    try:
        with open(path, 'wb', 0600) as output:
            while True:
                chunk = input.read(256*1024)
                if not chunk:
                    break
                output.write(chunk)
    finally:
        input.close()

@route('/ul/<hash_num>', method='POST')
def upload(hash_num):
    link = ROOT_WWW_FOLDER+'/'+hash_num
    if not os.path.exists(link):
        abort (404, 'Token not found!')
    try:
        file_data = request.files.data
        file_name = file_data.filename
    except:
        if os.path.exists(link):
            os.remove(link)
        abort(400, 'No file was specified!')
    up_path = os.path.realpath(link + '/' + file_name)
    if os.path.exists(up_path):
        abort(400, 'File already exists')
    if not up_path.startswith('/home'):
        abort(400, 'Invalid path.')
    linkstat = os.stat(link)
    os.remove(link)
    p = multiprocessing.Process(target=_upload_save,
            args=(linkstat.st_uid, linkstat.st_gid, file_data.file, up_path, ))
    try:
        p.start()
        p.join()
    finally:
        p.terminate()
    if p.exitcode:
        abort(400, 'Write failed.')
    try:
        redirect_address = request.headers.get('Referer')
    except:
        redirect_address = REDIRECT_URL
    response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    response.set_header('Access-Control-Allow-Headers', 'Content-Type, Content-Range, Content-Disposition, Content-Description')
    redirect(redirect_address)

# Return hard quota from quota
def hard_quota(quota):
    return str(int(int(quota)*1.25))

# Update users .ssh/authorized_keys
def updateSSHAuthorizedKeys(username, key_list):
    user_uid=getpwnam(username).pw_uid
    user_gid=getpwnam(username).pw_gid
    auth_file_name = "/home/"+username+"/authorized_keys"
    with open(auth_file_name, 'w') as auth_file:
        for key in key_list:
            auth_file.write(key+'\n')
    os.chmod(auth_file_name, 0600)
    os.chown(auth_file_name, user_uid, user_gid)
    return

# For debug purpose
# @route('/ul/<hash_num>', method='GET')
# def upload_get(hash_num):
#    return """<form method="POST" action="/ul/{hash}" enctype="multipart/form-data">
#   <input name="data" type="file" />
#   <input type="submit" />
# </form>""".format(hash=hash_num)

def list_directory(home, path):
    # Check for path breakout
    if not os.path.realpath(path).startswith(home):
        abort(400, 'Invalid path.')
    # Check if path exist
    if os.path.exists(path) != True:
        abort(404, 'No such file or directory')
    else:
        # If it's a file return with list
        if os.path.isdir(path) != True:
            return json.dumps((os.path.basename(path), 'F', os.path.getsize(path), os.path.getmtime(path)))
        # List directory and return list
        else:
            filelist = os.listdir(path)
            dictlist = [file_dict(os.path.join(path, f), home) for f in filelist]
            return json.dumps(dictlist)

def file_dict(path, home):
    basename = os.path.basename(path.rstrip('/'))
    if os.path.isdir(path):
        is_dir = 'D'
    else:
        is_dir = 'F'
    return {'NAME': basename,
            'TYPE': is_dir,
            'SIZE': os.path.getsize(path),
            'MTIME': os.path.getmtime(path),
            'DIR': os.path.relpath(os.path.dirname(path), home)}

def get_quota(neptun):
    output=subprocess.check_output([ROOT_BIN_FOLDER+'/'+USER_MANAGER, 'status', neptun], stderr=subprocess.STDOUT)
    return output.split()

def set_quota(neptun, quota):
    try:
        output=subprocess.check_output([ROOT_BIN_FOLDER+'/'+USER_MANAGER, 'setquota', neptun, quota, hard_quota(quota)], stderr=subprocess.STDOUT)
    except:
        return False
    return True

if __name__ == "__main__":
    run(host=SITE_HOST, port=SITE_PORT)
else:
    application=app()