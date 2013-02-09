#!/bin/bash
#
# Return values:
#   0: succesfully created
#   1: invalid syntax
#   2: user already exist
#


GRP_NAME="cloudusers"
COMMAND="$1"
USER_NAME="$2"
SMB_PASSWD="$3"
umask 022

        if [ "x${USER_NAME}" == "x" ]; then
            exit 1
        fi
case $COMMAND in
    'add')
        if [ "x${SMB_PASSWD}" == "x" ]; then
            exit 1
        fi
        if [ "x${SOFT_QUOTA}" == "x" ]; then
            exit 1
        fi
        if [ "x${HARD_QUOTA}" == "x" ]; then
            exit 1
        fi
        #Check if user already exist
        id ${USER_NAME} > /dev/null 2>&1
        if [ $? == '0' ]; then
            exit 2
        fi
        HOME_DIR="/home/${USER_NAME}/home"
        mkdir -p ${HOME_DIR}
        useradd --no-user-group --home ${HOME_DIR} --gid ${GRP_NAME} ${USER_NAME}  >/dev/null 2>&1
        adduser ${USER_NAME} ${GRP_NAME}  >/dev/null 2>&1
        chown ${USER_NAME}:cloudusers ${HOME_DIR}  >/dev/null 2>&1
        chmod 0755 ${HOME_DIR} >/dev/null 2>&1
        chmod 0755 "/home/${USER_NAME}" 2>&1
        #Set password to SMB_PASSWD
        echo -e "${SMB_PASSWD}\n${SMB_PASSWD}\n" | passwd ${USER_NAME} >/dev/null 2>&1
        #Set SMBPASSWD
        echo -e "${SMB_PASSWD}\n${SMB_PASSWD}" | (smbpasswd -a -s ${USER_NAME}) > /dev/null
        echo "User ${USER_NAME} CREATED at `date`" >> /root/users.log
        #Set quotas
        #           Username   Soft     Hard Inode Dev
#        setquota ${USER_NAME} 2097152 2621440 0 0 /home
        setquota ${USER_NAME} ${SOFT_QUOTA} ${HARD_QUOTA} 0 0 /home
        ;;
    'set')
        if [ "x${SMB_PASSWD}" == "x" ]; then
            exit 1
        fi
        id ${USER_NAME} > /dev/null 2>&1
        if [ $? == '0' ]; then
            echo -e "${SMB_PASSWD}\n${SMB_PASSWD}\n" | passwd ${USER_NAME} >/dev/null 2>&1
            echo -e "${SMB_PASSWD}\n${SMB_PASSWD}" | (smbpasswd -a -s ${USER_NAME}) > /dev/null
        else
            exit 2
        fi
        ;;
    'del')
        id ${USER_NAME} > /dev/null 2>&1
        if [ $? != '0' ]; then
            exit 2
        fi
        smbpasswd -x ${USER_NAME}  >/dev/null 2>&1
        deluser --remove-home ${USER_NAME}  >/dev/null 2>&1
        rmdir /home/${USER_NAME}  >/dev/null 2>&1
        echo "User ${USER_NAME} DELETED at `date`" >> /root/users.log
        ;;
    'stat')
        stat=( $(quota -w ${USER_NAME} 2>/dev/null | tail -1 | awk '{ print $2" "$3" "$4 }') )
        USED_DISK=${stat[0]}
        SOFT_LIMIT=${stat[1]}
        HARD_LIMIT=${stat[3]}
        case $3 in
            'used')
                echo $USED_DISK
                ;;
            'soft')
                echo $SOFT_LIMIT
                ;;
            'hard')
                echo $HARD_LIMIT
                ;;
        esac
        ;;
    'status')
        echo $(quota -w ${USER_NAME} 2>/dev/null | tail -1 | awk '{ print $2" "$3" "$4 }')
        ;;
    'setquota')
        SOFT_QUOTA="$3"
        HARD_QUOTA="$4"
        if [ "x${SOFT_QUOTA}" == "x" ]; then
            exit 1
        fi
        if [ "x${HARD_QUOTA}" == "x" ]; then
            exit 1
        fi
        setquota ${USER_NAME} ${SOFT_QUOTA} ${HARD_QUOTA} 0 0 /home
        ;;
    *)
        echo "Usage: UserManager.sh COMMAND USER PASSWORD"
        exit 1
        ;;
esac
