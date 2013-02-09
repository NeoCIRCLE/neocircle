#!/bin/bash

export BASEDIR=$(dirname $0)
export USER="cloud"
export HOME=$(awk -F: -v u=$USER '$1==u{print $6}' /etc/passwd)

mkdir -p "$BASEDIR/mnt"
cd "$BASEDIR"

mount -t iso9660 /dev/cdrom1 "$BASEDIR/mnt" 2> /dev/null

if [ $? -eq 0 -a -f "$BASEDIR/firstrun" -a -f "$BASEDIR/mnt/context.sh" ]; then
    . "$BASEDIR/mnt/context.sh"

    if [ "$RECONTEXT" != "YES" ]; then
        rm "$BASEDIR/firstrun"
    else
        touch /run/context-cleanup
    fi

    for i in $BASEDIR/init.d/*; do
        source $i
    done

else
    echo "mar korabban lefutott!"
fi

umount /dev/cdrom1 2>/dev/null
eject /dev/cdrom1
exit 0
