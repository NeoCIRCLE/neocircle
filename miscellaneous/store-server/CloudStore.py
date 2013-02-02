#!/usr/bin/python

# TODO File permission checks

from bottle import route, run, request, static_file, abort, redirect, app
import json, os, shutil
import uuid
import subprocess
import ConfigParser
from pwd import getpwnam

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
        statistics=getQuotaStatus(neptun)
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
    if( os.path.isfile(dl_path) ):
        os.symlink(dl_path, ROOT_WWW_FOLDER+'/'+dl_hash)
        # Debug
        # redirect('http://store.cloud.ik.bme.hu:8080/dl/'+dl_hash)
        return json.dumps({'LINK' : SITE_URL+'/dl/'+dl_hash})
    else:
        try:
            os.makedirs(TEMP_DIR+'/'+neptun, 0700)
        except:
            pass
        folder_name = os.path.basename(dl_path)
        temp_path = TEMP_DIR+'/'+neptun+'/'+folder_name+'.zip'
        with open(os.devnull, "w") as fnull:
            # zip -rqDj vmi.zip /home/tarokkk/vpn-ik
            result = subprocess.call(['/usr/bin/zip', '-rqDj', temp_path, dl_path], stdout = fnull, stderr = fnull)
        os.symlink(temp_path, ROOT_WWW_FOLDER+'/'+dl_hash)
        return json.dumps({'LINK' : SITE_URL+'/dl/'+dl_hash})
COMMANDS['DOWNLOAD'] = cmd_download

# UPLOAD
def cmd_upload(request, neptun, home_path):
    up_path = home_path+'/'+request.json['PATH']
    up_path = os.path.realpath(up_path)
    if not up_path.startswith(home_path):
        abort(400, 'Invalid upload path.')
    if os.path.exists(up_path) == True and os.path.isdir(up_path):
        up_hash = str(uuid.uuid4())
        os.symlink(up_path, ROOT_WWW_FOLDER+'/'+up_hash)
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
def cmd_new_folder(request, neptun, home_path):
    dir_path = home_path+'/'+request.json['PATH']
    dir_path = os.path.realpath(dir_path)
    if not dir_path.startswith(home_path):
        abort(400, 'Invalid directory path.')
    if os.path.exists(dir_path) == True:
        abort(400, "Directory already exist!")
    else:
        os.mkdir(dir_path, 0755)
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


@route('/new/<neptun>', method='POST')
@force_ssl
def new_user(neptun):
    key_list = []
    smbpasswd=''
    try:
        smbpasswd = request.json['SMBPASSWD']
    except:
        abort(400, 'Invalid syntax')
    # Call user creator script
    result = subprocess.call([ROOT_BIN_FOLDER+'/'+USER_MANAGER, 'add', neptun, smbpasswd])
    if result == 0:
        try:
            for key in request.json['KEYS']:
                key_list.append(key)
            updateSSHAuthorizedKeys(neptun, key_list)
        except:
            abort(400, 'SSH')
        return
    elif result == 2:
        abort(403, 'User already exist!')
    else:
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
@route('/ul/<hash_num>', method='POST')
def upload(hash_num):
    if not os.path.exists(ROOT_WWW_FOLDER+'/'+hash_num):
        abort (404, 'Token not found!')
    try:
        file_data = request.files.data
        file_name = file_data.filename
    except:
        if os.path.exists(ROOT_WWW_FOLDER+'/'+hash_num):
            os.remove(ROOT_WWW_FOLDER+'/'+hash_num)
        abort(400, 'No file was specified!')
    up_path = os.path.realpath(ROOT_WWW_FOLDER+'/'+hash_num+'/'+file_name)
    if os.path.exists(up_path):
        abort(400, 'File already exists')
    # Check if upload path valid
    if not up_path.startswith('/home'):
        abort(400, 'Invalid path.')
    os.remove(ROOT_WWW_FOLDER+'/'+hash_num)
    # Get the real upload path
    # Delete the hash link
    # Get the username from path for proper ownership
    username=up_path.split('/', 3)[2]
    # os.setegid(getpwnam(username).pw_gid)
    # os.seteuid(getpwnam(username).pw_uid)
    # TODO setuid subcommand
    # Check if file exist (root can overwrite anything not safe)
    f = open(up_path , 'wb')
    os.chown(up_path, getpwnam(username).pw_uid, getpwnam(username).pw_gid)
    os.chmod(up_path, 0644)
    f.close()
    with open(up_path , 'wb') as f:
        datalength = 0
        for chunk in fbuffer(file_data.file):
            f.write(chunk)
            datalength += len(chunk)
    return 'Upload finished: '+file_name+' - '+str(datalength)+' Byte'




# Define filebuffer for big uploads
def fbuffer(f, chunk_size=4096):
   while True:
      chunk = f.read(chunk_size)
      if not chunk: break
      yield chunk

# Update users .ssh/authorized_keys
def updateSSHAuthorizedKeys(username, key_list):
    user_home_ssh = '/home/'+username+'/home/.ssh'
    user_uid=getpwnam(username).pw_uid
    user_gid=getpwnam(username).pw_gid
    if not os.path.exists(user_home_ssh):
        os.mkdir(user_home_ssh, 0700)
    os.chown(user_home_ssh, user_uid, user_gid)
    auth_file_name = user_home_ssh+'/authorized_keys'
    auth_file = open(auth_file_name, 'w')
    for key in key_list:
        auth_file.write(key+'\n')
    auth_file.close()
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
            'SIZE': os.path.getsize(path)/1024,
            'MTIME': os.path.getmtime(path),
            'DIR': os.path.relpath(os.path.dirname(path), home)}

def getQuotaStatus(neptun):
    output=subprocess.check_output([ROOT_BIN_FOLDER+'/'+USER_MANAGER, 'status', neptun], stderr=subprocess.STDOUT)
    return output.split()

if __name__ == "__main__":
    run(host=SITE_HOST, port=SITE_PORT)
else:
    application=app()
