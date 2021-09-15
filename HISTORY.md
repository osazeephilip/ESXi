History
=====================

1.0alpha5 (2021-09-13)
---------------------
* removed root password when saving kickstart to job log
* removed Cisco logo
* removed 'Upload a CSV file' option (not implemented yet)

1.0alpha4 (2021-09-07)
---------------------
* removed disabling IPv6 and final reboot from kickstart template

1.0alpha3 (2021-08-30)
---------------------
* CIMC address allowing custom port (ip[:port])

1.0alpha (2021-07-30)
---------------------
* no PXE boot
* custom ISO is generated and mounted on target UCS machine using API call to CIMC

0.9demo (2021-01-10)
---------------------
* PXE booted installation with kickstart config
* requires Native VLAN and 'ip helper' / 'dhcp relay' set on switch
* dhcpd.conf update not validated in demo version
* configuration reset on VM reboot