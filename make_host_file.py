#!/usr/bin/env python
# Generate /etc/hosts files with AWS environments
# Kyle Squizzato <kyle.squizzato@docker.com>

import argparse
import sys
import os
import re
import paramiko
import logging
from scp import SCPClient

"""
setup ip files
"""
global private_ips, public_ips
private_ips = []
public_ips = []

"""
Build list of IPs from env_file
"""
def host_list(env_file):
    logging.info("Building a list of IP addresses from given file")
    # Read the IP's for each host from env_file
    f = open(env_file, "r")
    env_details = f.read(4096)
    f.close()
    pattern = '[\n\r].*IP:\\s*([^\n\r]*)'
    all_ips = re.findall(pattern, env_details)
    # Filter ips into associate private and public lists
    for each in all_ips:
        if each.startswith("10.0"):
            private_ips.append(each)
        else:
            public_ips.append(each)

"""
Get the default nametype, else just use the one the user gives us
"""
def get_nametype(env_file):
    logging.info("Determining the name to give each host")
    # Extract the nametype from the env_file name, for example docker-1.txt
    # would be docker
    sep = '-'
    nametype = os.path.splitext(os.path.basename(env_file))[0].split(sep, 1)[0]
    return nametype

"""
Expand ~ so that it correctly points to home directories
"""
#FIXME: Correclty expand homedir path if ~ is used in argparse
def expand_homedir(env_file):
    homedir = os.path.expanduser('~')
    full_env_path = homedir+env_file
    return full_env_path

"""
Generate host files for train env, syntax will match that of the env.txt file
"""
def generate_host_file(nametype, privaddrs=private_ips, pubaddrs=public_ips,
                       make_local=False):
    # Construct a string that generates a host file with the desired host
    # nametype, followed by the private IP.
    length = len(privaddrs)
    count = list(range(length))
    logging.info('Generating a host file for remote hosts')
    for each in privaddrs, count:
        logging.debug('appending host {0}{1} {2}'.format(nametype, count, each))
        host_file_string = "{0}{1} {2}".format(nametype, count, each)
        f = open("tmp_host_file", "w")
        f.write(host_file_string)
    f.close()
    # If make_local is set, also make a /etc/hosts file for the local host
    if make_local == True:
        logging.info('make-local flag detected, appending a local /etc/hosts \
file which contains public IP addresses')
        # it should be the same, but will set the length/count to the public
        # list
        length = len(pubaddrs)
        count = list(range(length))
        for each in pubaddrs, count:
            logging.debug('appending host file to /etc/hosts on local machine')
            host_file_string = "{0}{1} {2}".format(nametype, count, each)
            f = open("/etc/hosts", "a+")
            f.write(host_file_string)

"""
Copy the remote host files to each host
"""
def copy_host_files(keyfile, pubaddrs=public_ips):
    k = paramiko.RSAKey.from_private_key_file(keyfile)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logging.info('Copying host files to remote hosts')
    for each in pubaddrs:
        logging.debug('copying host file to {0}'.format(each))
        ssh.connect(each, username="ubuntu", pkey=k)
        scp = SCPClient(ssh.get_transport())
        scp.put("tmp_host_file", "/home/ubuntu/hosts")
        # Append the newly created hostfile into the existing hosts file on
        # each host
        ssh.exec_command("sudo cat /home/ubuntu/hosts >> /etc/hosts")
    logging.info('All host files copied to remote hosts')

def main():
    # logging
    logger = logging.getLogger(name=None)
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.DEBUG
                        )

    # argument parsing
    global args
    parser = argparse.ArgumentParser(description='Generate and copy a host file \
                                    to docker environments initially setup \
                                    with train.')
    parser.add_argument("-N",
                        dest="nametype",
                        help="Define a hostname to use to identify hosts in \
                        your deployed environment.")
    parser.add_argument("-i",
                        dest="ssh_identity_file",
                        help="Specify the location where your SSH identity \
                        file resides for AWS (normally in your train \
                        directory).",
                        required=True)
    parser.add_argument("-f",
                        dest="env_file",
                        help="Specify the location/name of the environment.txt \
                        file found inside of your train directory.  This is \
                        used to read IP's of the hosts.",
                        required=True)
    parser.add_argument("--make-local",
                        dest="make_local",
                        action="store_true",
                        help="Add entries to the hosts in your local \
                        /etc/hosts file (requires root) using the public IP's \
                        for each host.")

    args = parser.parse_args()

    # Generate host list
    host_list(args.env_file)

    # Get default nametype
    if args.nametype == None:
        nametype = get_nametype(args.env_file)
    else:
        nametype = args.nametype
    # announce the nametype we'll use
    logging.info("Will use name: {0}".format(nametype))

    # Generate a hosts file
    if args.make_local == True:
        generate_host_file(nametype, make_local=True)
    else:
        generate_host_file(nametype)

    # Copy remote hosts
    copy_host_files(args.ssh_identity_file)

    # Tell users we're done
    logging.info("All tasks complete.")

"""
Main
"""
if __name__ == '__main__':
    sys.exit(main())
