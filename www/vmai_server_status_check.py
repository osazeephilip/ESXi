from vmai_functions import *
from config import *
# from config_local import *
from time import sleep

if __name__ == "__main__":
    print_vmai_db()
    with open(VMAI_DB, 'r') as vmaidb_file:
        vmaidb = json.load(vmaidb_file)
    print("{:25} {:20} {:20} {:30}"
          .format('Hostname', 'MAC address', 'IP Address', 'STATUS'))
    for host in vmaidb.items():
        if host[1]['STATUS'] in 'Ready to deploy':
            # as we currently don't check if the installation is actually in progress
            # let's simply set status to 'Installation in progress' for new hosts
            host[1]['STATUS'] = 'Installation in progress'
            # check current server status
        else:
            status = deployment_status(host[1]['IPADDR'], host[1]['MAC'])
            # check if deployment status has changed and update VMAI_DB accordingly
            if status not in host[1]['STATUS'] and host[1]['STATUS'] not in 'Finished':
                host[1]['STATUS'] = status
        print("{:25} {:20} {:20} {:30}"
              .format(host[0], host[1]['MAC'], host[1]['IPADDR'], host[1]['STATUS']))
    with open(VMAI_DB, 'w') as vmaidb_file:
        json.dump(vmaidb, vmaidb_file, ensure_ascii=False, indent=2)
    print('')
