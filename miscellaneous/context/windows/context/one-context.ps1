#################################################################
##### Windows Powershell Script to configure OpenNebula VMs #####
#####   Created by andremonteiro@ua.pt and tsbatista@ua.pt  #####
#####        DETI/IEETA Universidade de Aveiro 2011         #####
#################################################################

Set-ExecutionPolicy unrestricted -force # not needed if already done once on the VM
[string]$computerName = "$env:computername"
[string]$ConnectionString = "WinNT://$computerName"
[string]$username = "cloud"

function getContext($file) {
        $context = @{}
        switch -regex -file $file {
                '(.+)="(.+)"' {
                        $name,$value = $matches[1..2]
                        $context[$name] = $value
                }
        }
        return $context
}

function addLocalUser($context) {

    # Create new user
        $ADSI = [adsi]$ConnectionString

        if(!([ADSI]::Exists("WinNT://$computerName/$username"))) {  
           $user = $ADSI.Create("user",$username)
           $user.setPassword($context["USERPW"])
           $user.SetInfo()
        }
        # Already exists, change password
        else{
        
           $admin=[ADSI]("WinNT://$computerName/$username, user")
           $admin.psbase.invoke("SetPassword", $context["USERPW"])
        }
    
    # Add user to local Administrators    
    $groups = "Administrators", "Administradores"
        
    foreach ($grp in $groups) {
    if([ADSI]::Exists("WinNT://$computerName/$grp,group")) {  
                $group = [ADSI] "WinNT://$computerName/$grp,group"
                        if([ADSI]::Exists("WinNT://$computerName/$username")) {  
                                $group.Add("WinNT://$computerName/$username")
                        }
                }
        }
}

function renameComputer($context) {
    $ComputerInfo = Get-WmiObject -Class Win32_ComputerSystem  
    $ComputerInfo.rename($context["HOSTNAME"])
}

function enableipv6($context)
{
    $interface="BME"
    $mac = (gwmi win32_NetworkAdapter -filter "NetConnectionID='BME'").MACAddress.split(':')
    $a = [Convert]::ToInt32($mac[3], 16)
    $b = [Convert]::ToInt32($mac[4], 16)
    $c = [Convert]::ToInt32($mac[5], 16)
    $ipv6="2001:738:2001:4031:{0}:{1}:{2}:0" -f $a, $b, $c
    $gwv6="2001:738:2001:4031:{0}:{1}:{2}:0" -f $a, 255, 254

    netsh interface ipv6 add address "$interface" "$ipv6/80"
    netsh interface ipv6 add route ::/0 "$interface" "$gwv6"
}

function enableRemoteDesktop()
{
    # Windows 7 only - add firewall exception for RDP
    netsh advfirewall Firewall set rule group="Remote Desktop" new enable=yes
    
    # Enable RDP
    $Terminal = (Get-WmiObject -Class "Win32_TerminalServiceSetting" -Namespace root\cimv2\terminalservices).SetAllowTsConnections(1)
    return $Terminal
}

function setacl($file)
{
    $userAccount = "\\someserver\auser"
    $aclWork = (Get-Item $file).GetAccessControl("Access")
    $netStuff = New-Object system.Security.AccessControl.FileSystemAccessRule($username, "FullControl", "ContainerInherit, ObjectInherit", "None", "Allow")
    $aclWork.SetAccessrule($netStuff)
    Set-ACL $file $aclWork
}

function storage($context)
{
    $smbpw = $context["SMBPW"]
    $smbuser = $context["NEPTUN"]
    $server = $context["SERVER"]
    $smbpw = $smbpw -replace "`"", "\`""
    mkdir c:\Windows\System32\Repl\Import\Scripts
    net user $username /scriptpath:$username
    echo "net use * /delete /yes `r`n timeout 10 `r`n net use z: \\$server\$smbuser `"$smbpw`" /user:$smbuser `r`n powershell Set-ItemProperty -Path 'HKCU:\HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -Name Personal -Value Z:\" | Out-File -encoding ASCII ("c:\Windows\System32\Repl\Import\Scripts\$username.bat")
    setacl("c:\Windows\System32\Repl\Import\Scripts")
    if($context["RECONTEXT"] -eq "YES") {
    
        echo "del c:\Windows\System32\Repl\Import\Scripts\$username.bat `r`n net use z: /delete" | Out-File -encoding ASCII ("c:\context\logoff.bat")
    } else {
        echo " " | Out-File -encoding ASCII ("c:\context\logoff.bat")
    }
}

function booturl($context)
{
    $token = $context["BOOTURL"]
    (new-object System.Net.WebClient).DownloadFile( $token, "c:\context\booturl")
}

# If folder context doesn't exist create it
if (-not (Test-Path "c:\context\")) {
    New-Item "C:\context\" -type directory
    }
    
# Execute script    
if( -not(Test-Path "c:\context\contextualized") -and (Test-Path "D:\context.sh")) {
    $context = @{} 
    $context = getContext('D:\context.sh')

    addLocalUser($context)
#    renameComputer($context)
    storage($context)
    enableipv6($context)
    enableRemoteDesktop
    booturl($context)

    if(-not($context["RECONTEXT"] -eq "YES")) {
        echo "contextualized" |Out-File ("c:\context\contextualized")
    }
}
