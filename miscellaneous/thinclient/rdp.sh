#!/bin/bash

IFS=: read scheme user password host port<<<"$*"

case $scheme in
rdp)
	tmp=$(mktemp)
	rdesktop -khu -E -P -0 -f -u "$user" -p "$password" "$host":"$port" 2>$tmp
	if grep '^ERROR' <$tmp
	then
		err="$(grep '^ERROR' $tmp)"
		rm /home/user/.ssh/known_hosts
		/usr/NX/bin/nxclient --dialog error --message "$err" &
	fi
	rm $tmp
;;
nx)
	f=$(mktemp)
	#pw=$(perl /usr/local/bin/enc.pl "$password"|tail -1|sed -e 's/\&/\&amp;/g' -e 's/</\&lt;/g' -e 's/"/&quot;/g' -e "s/'/\&apos;/g")
	pw=$(perl /usr/local/bin/enc.pl "$password"|tail -1)
	cat >"$f" <<A
<!DOCTYPE NXClientSettings>
<NXClientSettings application="nxclient" version="1.3" >
<group name="Advanced" >
<option key="Cache size" value="16" />
<option key="Cache size on disk" value="64" />
<option key="Current keyboard" value="true" />
<option key="Custom keyboard layout" value="" />
<option key="Disable DirectDraw" value="false" />
<option key="Disable ZLIB stream compression" value="false" />
<option key="Disable deferred updates" value="false" />
<option key="Enable HTTP proxy" value="false" />
<option key="Enable SSL encryption" value="true" />
<option key="Enable response time optimisations" value="false" />
<option key="Grab keyboard" value="false" />
<option key="HTTP proxy host" value="" />
<option key="HTTP proxy port" value="8080" />
<option key="HTTP proxy username" value="" />
<option key="Remember HTTP proxy password" value="false" />
<option key="Restore cache" value="true" />
<option key="StreamCompression" value="" />
</group>
<group name="Environment" >
<option key="CUPSD path" value="/usr/sbin/cupsd" />
</group>
<group name="General" >
<option key="Automatic reconnect" value="true" />
<option key="Command line" value="" />
<option key="Custom Unix Desktop" value="console" />
<option key="Desktop" value="gnome" />
<option key="Disable SHM" value="false" />
<option key="Disable emulate shared pixmaps" value="false" />
<option key="Link speed" value="lan" />
<option key="Remember password" value="true" />
<option key="Resolution" value="fullscreen" />
<option key="Resolution height" value="600" />
<option key="Resolution width" value="800" />
<option key="Server host" value="${host}" />
<option key="Server port" value="${port}" />
<option key="Session" value="unix" />
<option key="Spread over monitors" value="false" />
<option key="Use default image encoding" value="0" />
<option key="Use render" value="true" />
<option key="Use taint" value="true" />
<option key="Virtual desktop" value="false" />
<option key="XAgent encoding" value="true" />
<option key="displaySaveOnExit" value="true" />
<option key="xdm broadcast port" value="177" />
<option key="xdm list host" value="localhost" />
<option key="xdm list port" value="177" />
<option key="xdm mode" value="server decide" />
<option key="xdm query host" value="localhost" />
<option key="xdm query port" value="177" />
</group>
<group name="Images" >
<option key="Disable JPEG Compression" value="0" />
<option key="Disable all image optimisations" value="false" />
<option key="Disable backingstore" value="false" />
<option key="Disable composite" value="false" />
<option key="Image Compression Type" value="3" />
<option key="Image Encoding Type" value="0" />
<option key="Image JPEG Encoding" value="false" />
<option key="JPEG Quality" value="6" />
<option key="RDP Image Encoding" value="3" />
<option key="RDP JPEG Quality" value="6" />
<option key="RDP optimization for low-bandwidth link" value="false" />
<option key="Reduce colors to" value="" />
<option key="Use PNG Compression" value="true" />
<option key="VNC JPEG Quality" value="6" />
<option key="VNC images compression" value="3" />
</group>
<group name="Login" >
<option key="Auth" value="${pw}" />
<option key="Guest Mode" value="false" />
<option key="Guest password" value="" />
<option key="Guest username" value="" />
<option key="Login Method" value="nx" />
<option key="User" value="${user}" />
</group>
<group name="Services" >
<option key="Audio" value="false" />
<option key="IPPPort" value="631" />
<option key="IPPPrinting" value="false" />
<option key="Shares" value="false" />
</group>
<group name="VNC Session" >
<option key="Display" value="0" />
<option key="Remember" value="false" />
<option key="Server" value="" />
</group>
<group name="Windows Session" >
<option key="Application" value="" />
<option key="Authentication" value="2" />
<option key="Color Depth" value="8" />
<option key="Domain" value="" />
<option key="Image Cache" value="true" />
<option key="Password" value="EMPTY_PASSWORD" />
<option key="Remember" value="true" />
<option key="Run application" value="false" />
<option key="Server" value="" />
<option key="User" value="" />
</group>
<group name="share chosen" >
<option key="Share number" value="0" />
</group>
</NXClientSettings>
A
	/usr/NX/bin/nxclient --session $f
;;
ssh)
	#/usr/NX/bin/nxclient --dialog ok --message "Jelszó: $password" &
	rm /home/user/.ssh/known_hosts
	#rxvt-unicode -e sh -c "ssh $user@$host -p$port; sleep 2"
	rxvt-unicode -e sh -c "sshpass -p "$password" ssh -o StrictHostKeyChecking=no $user@$host -p$port; sleep 2"
;;
*)
	xmessage "$scheme is not supported."
;;
esac
echo "$*" >>/tmp/protolog 
