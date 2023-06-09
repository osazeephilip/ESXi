# Auxiliary funtions library

from asyncio.log import logger
from netifaces import gateways, ifaddresses, AF_INET
from ipaddress import ip_network
from jinja2 import Template
from config import *
from generic_functions import *


def get_host_network_settings():
    """
    Get host IP address, Gateway IP address, Subnet and Netmask.

    :param n/a
    :return: (tuple of str) Host IP address, Gateway IP address, Subnet, Netmask
    """

    # find IPv4 (AF_INET) address and NIC for default gateway
    get_gateways = gateways()["default"]
    gw_ip = get_gateways[AF_INET][0]
    gw_nic = get_gateways[AF_INET][1]

    # get network settings for NIC used for default gateway
    nic_addrs = ifaddresses(gw_nic)[AF_INET]
    # in case there were more IP addresses on gw_nic - search for the one on same subnet
    for nic_addr in nic_addrs:
        netmask = nic_addr["netmask"]
        nic_ip = nic_addr["addr"]
        nic_subnet = ip_network(nic_ip + "/" + netmask, strict=False).network_address
        gw_subnet = str(ip_network(gw_ip + "/" + netmask, strict=False).network_address)
        if gw_subnet == nic_subnet:
            # stop when we find IP address on same subnet as default gateway
            break
        return nic_ip, gw_ip, gw_subnet, netmask


def generate_dhcp_config(
    jobid,
    logger,
    mainlog,
    eai_ip=EAIHOST_IP,
    eai_gw=EAIHOST_GW,
    eai_subnet=EAIHOST_SUBNET,
    eai_mask=EAIHOST_NETMASK,
    dhcpd_tpl=DHCPD_CONF_TPL,
    dhcpd_conf_path=DHCPD_CONF,
):
    """
    Generate dhcpd.conf configuration file main configuration file and custom host entries

    :param jobid: (str) job ID
    :param logger: (logging.Handler) logger handler for jobid
    :param mainlog: (logging.Handler) main Auto-Installer logger handler
    :param eai_ip: (str) IP address of host where EAI container is running
    :param eai_gw: (str) Gateway IP address of host where EAI container is running
    :param eai_subnet: (str) Subnet address of host where EAI container is running
    :param eai_subnet: (str) Network mask of host where EAI container is running
    :param dhcpd_tpl: (path) path to dhcpd.conf jinja template
    :param dhcpd_conf_path: (path) path to dhcpd.conf configuration file
    :return: n/a
    """

    logger.info("Updating DHCP Server configuration")

    # dhcpd.conf main section
    with open(dhcpd_tpl, "r") as f:
        dhcpd_conf_template = Template(f.read())

    dhcpd_content = dhcpd_conf_template.render(
        nextserver=eai_ip,
        subnet=eai_subnet,
        netmask=eai_mask,
        ipaddr=eai_ip,
        gateway=eai_gw,
    )

    # Render subnets
    dhcpd_content += generate_dhcp_subnet_entries(
        mainlog, ip_network(f"{eai_subnet}/{eai_mask}").with_netmask
    )

    # Render host entries
    host_entries = generate_dhcp_host_entries(mainlog)
    if len(host_entries):
        for entry in host_entries:
            dhcpd_content += entry

    with open(dhcpd_conf_path, "w+") as dhcpd_conf:
        dhcpd_conf.write(dhcpd_content)


def generate_dhcp_subnet_entries(
    mainlog, filtersubnet, eaidb=EAIDB, dhcp_subnet_tpl=DHCP_SUBNET_TPL
):
    # read EAIDB
    eaidb_dict = eaidb_get_status(eaidb)
    subnets = []
    for job_entry in eaidb_dict.items():
        # Since the eaidb_get_status command returns all records, not just the records want, it has to be filtered.
        # If this is a DHCP installation
        if job_entry[1]["macaddr"]:
            # Calculate the IP subnet address
            subnet = ip_network(
                f"{job_entry[1]['ipaddr']}/{job_entry[1]['netmask']}", strict=False
            ).with_netmask
            # Check if it's unique
            if subnet not in subnets and subnet != filtersubnet:
                # Add to the list of subnets to generate
                subnets.append(subnet)
    # If we found any subnets, generate the subnets.
    if subnets:
        with open(dhcp_subnet_tpl, "r") as f:
            dhcpd_conf_subnets = Template(f.read())
        mainlog.debug(f"Generated {len(subnets)} subnet entries for dhcpd.conf")
        return dhcpd_conf_subnets.render(subnets=subnets)
    return ""


def generate_dhcp_host_entries(
    mainlog, eaidb=EAIDB, dhcp_host_tpl=DHCP_HOST_TPL, status_dict=STATUS_CODES
):
    """
    Generate host entries part of dhcpd.conf based on entries in EAIDB in state 'Ready to deploy'.
    This function get's called by generate_dhcp_config() which first generates mains dhcpd.conf configuration section.

    :param mainlog: (logging.Handler) main Auto-Installer logger handler
    :param eaidb: (path) path to EAIDB sqlite database
    :param dhcp_host_tpl: (path) path to DHCP host entry jinja template
    :return: (list) host entries in the following format:

            ## custom entries for {{hostname}} ###
            host {{hostname}} {
              hardware ethernet {{macaddr}};
              fixed-address {{ipaddr}};
            }
            ## end of custom entries for {{hostname}} ###
    """

    # read dhcp host entry jinja template
    with open(dhcp_host_tpl, "r") as dhcp_template:
        dhcp_host_entry = Template(dhcp_template.read())

    # read EAIDB
    eaidb_dict = eaidb_get_status(eaidb)
    hosts = []
    for job_entry in eaidb_dict.items():
        # ignore jobs that finished/errored
        # Techincally do not need code 15 since as of Dec 2022 it is only used by CIMC.
        if job_entry[1]["macaddr"] and (
            job_entry[1]["status"] == status_dict[0]
            or job_entry[1]["status"] == status_dict[15]
            or job_entry[1]["status"] == status_dict[16]
        ):
            if any(f"host {job_entry[1]['hostname']}" in s for s in hosts):
                # hostname has to be unique in dhcpd.conf - skip entries with same hostname
                print(
                    f"[SKIPPING] {job_entry[0]} Skipping host entry - hostname {job_entry[1]['hostname']} already in use"
                )
                continue
            else:
                # generate host entry for each job with unique hostname and 'Ready to deploy' status
                subnet = ip_network(
                    job_entry[1]["ipaddr"] + "/" + job_entry[1]["netmask"], strict=False
                ).network_address

                host_entry = dhcp_host_entry.render(
                    hostname=job_entry[1]["hostname"],
                    subnet=subnet,
                    netmask=job_entry[1]["netmask"],
                    ipaddr=job_entry[1]["ipaddr"],
                    gateway=job_entry[1]["gateway"],
                    macaddr=job_entry[1]["macaddr"],
                )
                hosts.append(host_entry)

    mainlog.debug(f"Generated {len(hosts)} host entries for dhcpd.conf")
    # from pprint import pprint
    # pprint(hosts)
    return hosts
