#!/bin/bash

export BASEDIR=$(dirname $0)
export USER="cloud"
export HOME=$(awk -F: -v u=$USER '$1==u{print $6}' /etc/passwd)

cd "$BASEDIR"

mount -t iso9660 /dev/cdrom1 "$BASEDIR/mnt" 2> /dev/null

if [ $? -eq 0 -a -f "$BASEDIR/firstrun" -a -f "$BASEDIR/mnt/context.sh" ]; then
	. "$BASEDIR/mnt/context.sh"

	# hogy tudom kiexportalni ennel szebben ezeket a valtozokat?
	eval `grep -o '^[a-zA-Z0-9]\+=' "$BASEDIR/mnt/context.sh" | while read x; do echo export ${x%=};done`

	run-parts "$BASEDIR/init.d"

	rm "$BASEDIR/firstrun"
else
	echo "mar korabban lefutott!"
fi

umount /dev/cdrom1 2>/dev/null
eject /dev/cdrom1
exit 0
