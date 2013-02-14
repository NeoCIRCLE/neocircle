#!/bin/bash
#
# OpenNebula automatic node setup

set -ve

STORAGE_IP="10.3.1.1"
STORAGE_IP_IB="172.22.1.1"
ONEADMIN_HOME="/var/lib/one"
ONEUID=200


#apt-get update

#
# Initialize oneadmin user and nfs mounts
#

#SetUp oneadmin environment
echo "Add oneadmin user."
grep oneadmin:x:200 /etc/passwd ||
adduser --disabled-password --uid $ONEUID --home ${ONEADMIN_HOME} oneadmin

if grep datastore /etc/fstab
then
	echo Skip configuring NFS.
else
	echo eth/ib?
	read NET
	#Install NFS
	apt-get -y install nfs-common vim-nox language-pack-hu
	sed -i 's/^# Domain.*/Domain = cloud.ik.bme.hu/' /etc/idmapd.conf
	restart idmapd
	#Create datastore and mounts
	mkdir -p /datastore
	chown oneadmin:oneadmin /datastore
	#Add mount options to fstab
	case "$NET" in
	eth)
	    cat << EOF >> /etc/fstab 
	    #NFS datastore
	    ${STORAGE_IP}:/datastore   /datastore      nfs     rw       0       0 
	    ${STORAGE_IP}:/oneadmin_home       /var/lib/one    nfs    rw      0       0 
EOF
	;;
	ib)
	    cat << EOF >> /etc/fstab 
	    #NFS datastore
	    ${STORAGE_IP_IB}:/datastore   /datastore      nfs     rw       0       0 
	    ${STORAGE_IP_IB}:/oneadmin_home       /var/lib/one    nfs    rw      0       0 
EOF
	;;
	*)
	     echo "Unknown NET parameter exiting..."
	     exit 1;
	;;
	esac
	#Remount from fstab
	mount -a
fi

echo "Add oneadmin sudoer command."
if ! grep ^oneadmin /etc/sudoers
then
	echo -e "\noneadmin ALL= (ALL) NOPASSWD: /usr/bin/ovs-vsctl\noneadmin ALL= (ALL) NOPASSWD: /usr/bin/ovs-ofctl
" >> /etc/sudoers
fi

#Copy files from mounted home
cp ${ONEADMIN_HOME}/setup/rc.local /etc/rc.local
#
# Install OpenVSwitch
#
#Fist blacklist the bridge module
if ! grep bridge /etc/modprobe.d/blacklist.conf
then
cat <<EOF >>/etc/modprobe.d/blacklist.conf
blacklist bridge
EOF
fi
#Install OpenVSwitch
umount /var/lib/one
apt-get install openvswitch-brcompat openvswitch-switch openvswitch-controller
sed -i 's/^# BRCOMPAT.*/BRCOMPAT=yes/' /etc/default/openvswitch-switch
/etc/init.d/openvswitch-switch restart


#
#Install opennebula_node package
#
apt-get install opennebula-node kvm qemu-utils

mount /var/lib/one

#Copy libvirt default configuration
cp ${ONEADMIN_HOME}/setup/qemu.conf /etc/libvirt/qemu.conf 
cp ${ONEADMIN_HOME}/setup/libvirtd.conf  /etc/libvirt/libvirtd.conf

#Enbale opennebula to use the kvm
addgroup oneadmin kvm
addgroup oneadmin cloud

#ssh
mkdir /root/.ssh
cp ${ONEADMIN_HOME}/setup/authorized_keys_root /root/.ssh/authorized_keys
chown root:root /root/.ssh/authorized_keys
chown root:root -R /root/.ssh

/etc/init.d/libvirt-bin restart

echo "Installation finished please reboot!"

