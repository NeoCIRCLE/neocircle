#!/usr/bin/python

#TODO File permission checks

from bottle import route, run, request, static_file, abort, redirect, app
import json, os, shutil
import uuid
import subprocess
import ConfigParser
from pwd import getpwnam

#Get configuration file
config = ConfigParser.ConfigParser()
config.read('store.config')


#ROOT_WWW_FOLDER='/var/www'
ROOT_WWW_FOLDER = config.get('store', 'root_www_folder')
#ROOT_BIN_FOLDER='/opt/store-server'
ROOT_BIN_FOLDER = config.get('store', 'root_bin_folder')
#SITE_URL='http://store.cloud.ik.bme.hu:8080'
SITE_URL = config.get('store', 'site_url')
#USER_MANAGER='UserManager.sh'
USER_MANAGER = config.get('store', 'user_manager')
#Standalone server
SITE_HOST = config.get('store', 'site_host')
SITE_PORT = config.get('store', 'site_port')

@route('/')
def index():
    response = "NONE"
    try:
        response = request.environi.get('SSL_CLIENT_VERIFY', 'NONE')
    except:
        pass
    return "It works! SSL: "+response

#@route('/<neptun:re:[a-zA-Z0-9]{6}>', method='GET')
@route('/<neptun>', method='GET')
def neptun_GET(neptun):
    home_path = '/home/'+neptun+'/home'
    if os.path.exists(home_path) != True:
        abort(401, 'The requested user does not exist!')
    else:
        statistics=getQuotaStatus(neptun)
        return { 'Used' : statistics[0], 'Soft' : statistics[1], 'Hard' : statistics[2]}

@route('/<neptun>', method='POST')
def neptun_POST(neptun):
    #Check if user avaiable (home folder ready)
    home_path = '/home/'+neptun+'/home'
    if os.path.exists(home_path) != True:
        abort(401, 'The requested user does not exist!')
    else:
        #Parse post
        #LISTING
        if request.json['CMD'] == 'LIST':
            list_path = home_path+request.json['PATH']
            if os.path.exists(list_path) != True:
                abort(404, "Path not found!")
            else:
                return list_directory(home_path,list_path)
        #DOWNLOAD LINK GENERATOR
        elif request.json['CMD'] == 'DOWNLOAD':
            dl_path = home_path+'/'+request.json['PATH']
            dl_path = os.path.realpath(dl_path)
            if not dl_path.startswith(home_path):
                abort(400, 'Invalid download path.') 
            if( os.path.isfile(dl_path) ):
                dl_hash = str(uuid.uuid4())
                os.symlink(dl_path, ROOT_WWW_FOLDER+'/'+dl_hash)
                #Debug 
                #redirect('http://store.cloud.ik.bme.hu:8080/dl/'+dl_hash)
                return json.dumps({'LINK' : SITE_URL+'/dl/'+dl_hash})
            else:
                abort(400, 'Can\'t download folder')
        #UPLOAD
        elif request.json['CMD'] == 'UPLOAD':
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
        #MOVE 
        elif request.json['CMD'] == 'MOVE':
            src_path = home_path+'/'+request.json['SOURCE']
            dst_path = home_path+'/'+request.json['DESTINATION']
            src_path = os.path.realpath(src_path)
            dst_path = os.path.realpath(dst_path)
            if not src_path.startswith(home_path):
                abort(400, 'Invalid source path.')
            if not dst_path.startswith(home_path):
                abort(400, 'Invalid destination path.')
            if os.path.exists(src_path) == True and os.path.exists(dst_path) == True and os.path.isdir(dst_path) == True:
                shutil.move(src_path,dst_path)
                return
            else:
            #TODO
                abort(400, "Can not move the file.")
        #RENAME
        elif request.json['CMD'] == 'RENAME': 
            src_path = home_path+'/'+request.json['PATH']
            src_path = os.path.realpath(src_path)
            if not src_path.startswith(home_path):
                abort(400, 'Invalid source path.')
            dst_path = os.path.dirname(src_path)+'/'+request.json['NEW_NAME']
            if os.path.exists(src_path) == True:
                os.rename(src_path, dst_path)
            else:
                abort(404, "File or Folder not found!")
            return
        #NEW FOLDER
        elif request.json['CMD'] == 'NEW_FOLDER':
            dir_path = home_path+'/'+request.json['PATH']
            dir_path = os.path.realpath(dir_path)
            if not dir_path.startswith(home_path):
                abort(400, 'Invalid directory path.')
            if os.path.exists(dir_path) == True:
                abort(400, "Directory already exist!")
            else:
                os.mkdir(dir_path, 0755)
                return
        #REMOVE
        elif request.json['CMD'] == 'REMOVE':
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
        else:
            abort(400, "Command not found!")

@route('/set/<neptun>', method='POST')
def set_keys(neptun):
    key_list = []
    smb_password = ''
    try:
        smbpasswd = request.json['SMBPASSWD']
        for key in request.json['KEYS']:
            key_list.append(key)
    except:
        abort(400, 'Wrong syntax!')
    result = subprocess.call([ROOT_BIN_FOLDER+'/'+USER_MANAGER,'set',neptun,smbpasswd])
    if result == 0:
        updateSSHAuthorizedKeys(neptun,key_list)
        return
    elif result == 2:
        abort(403, 'User does not exist!')


@route('/new/<neptun>', method='POST')
def new_user(neptun):
    key_list = []
    smbpasswd=''
    try: 
        smbpasswd = request.json['SMBPASSWD']
    except:
        abort(400, 'Invalid syntax')
    #Call user creator script
    result = subprocess.call([ROOT_BIN_FOLDER+'/'+USER_MANAGER,'add',neptun,smbpasswd])
    if result == 0:
        try:
            for key in request.json['KEYS']:
                key_list.append(key)
            updateSSHAuthorizedKeys(neptun,key_list)
        except:
            abort(400,'SSH')
        return
    elif result == 2:
        abort(403, 'User already exist!')
    else:
        abort(400, 'An error occured!')

    

#Static file
@route('/dl/<hash_num>', method='GET')
def dl_hash(hash_num):
    hash_path = ROOT_WWW_FOLDER 
    if os.path.exists(hash_path) != True:
        abort(404, "File not found!")
    else:
        filename = os.path.basename(os.path.realpath(hash_path+'/'+hash_num))
        return static_file(hash_num,root=hash_path,download=filename)
@route('/ul/<hash_num>', method='POST')            
def upload(hash_num):
    if not os.path.exists(ROOT_WWW_FOLDER+'/'+hash_num):
        abort (404,'Token not found!')
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
    #Check if upload path valid
    if not up_path.startswith('/home'):
        abort(400, 'Invalid path.')
    os.remove(ROOT_WWW_FOLDER+'/'+hash_num)
    #Get the real upload path
    #Delete the hash link
    #Get the username from path for proper ownership
    username=up_path.split('/',3)[2]
    #os.setegid(getpwnam(username).pw_gid)
    #os.seteuid(getpwnam(username).pw_uid)
    #TODO setuid subcommand
    #Check if file exist (root can overwrite anything not safe)
    f = open(up_path , 'wb')
    datalength = 0
    for chunk in fbuffer(file_data.file):
        f.write(chunk)
        datalength += len(chunk)
    f.close()
    os.chown(up_path,getpwnam(username).pw_uid,getpwnam(username).pw_gid)
    os.chmod(up_path,0644)
    return 'Upload finished: '+file_name+' - '+str(datalength)+' Byte'




#Define filebuffer for big uploads
def fbuffer(f, chunk_size=4096):
   while True:
      chunk = f.read(chunk_size)
      if not chunk: break
      yield chunk

#Update users .ssh/authorized_keys
def updateSSHAuthorizedKeys(username,key_list):
    user_home_ssh = '/home/'+username+'/home/.ssh'
    user_uid=getpwnam(username).pw_uid
    user_gid=getpwnam(username).pw_gid
    if not os.path.exists(user_home_ssh):
        os.mkdir(user_home_ssh, 0700)
    os.chown(user_home_ssh,user_uid,user_gid)
    auth_file_name = user_home_ssh+'/authorized_keys'
    auth_file = open(auth_file_name,'w')
    for key in key_list:
        auth_file.write(key+'\n')
    auth_file.close()
    os.chmod(auth_file_name,0600)
    os.chown(auth_file_name,user_uid,user_gid)
    return

#For debug purpose
#@route('/ul/<hash_num>', method='GET')
#def upload_get(hash_num):
#    return """<form method="POST" action="/ul/{hash}" enctype="multipart/form-data">
#   <input name="data" type="file" />
#	<input type="submit" />
#</form>""".format(hash=hash_num)

def list_directory(home,path):
    #Check for path breakout
    if not os.path.realpath(path).startswith(home):
        abort(400, 'Invalid path.')
    #Check if path exist
    if os.path.exists(path) != True:
        abort(404,'No such file or directory')
    else:
        #If it's a file return with list
        if os.path.isdir(path) != True:
            return json.dumps((os.path.basename(path), 'F', os.path.getsize(path), os.path.getmtime(path)))
        #List directory and return list
        else:
            tuplelist = []
            filelist = os.listdir(path)
        #Add type support
            for item in filelist:
                static_route = path+"/"+item
                if os.path.isdir(static_route):
                    is_dir = 'D'
                else:
                    is_dir = 'F'
                element = { 'NAME' : item, 'TYPE' : is_dir, 'SIZE' : os.path.getsize(static_route)/1024, 'MTIME' : os.path.getmtime(static_route) }
                tuplelist.append(element)
            return json.dumps(tuplelist)

def getQuotaStatus(neptun):
    output=subprocess.check_output([ROOT_BIN_FOLDER+'/'+USER_MANAGER,'status',neptun], stderr=subprocess.STDOUT)
    return output.split()
    
if __name__ == "__main__":
    run(host=SITE_HOST, port=SITE_PORT)
else:
    application=app()
