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
def expand_homedir(env_file):
    full_env_path = os.path.expanduser(env_file)
    return full_env_path

"""
Generate host files for train env, syntax will match that of the env.txt file
"""
def generate_host_file(nametype, privaddrs=private_ips, pubaddrs=public_ips,
                       make_local=False, make_local_only=False, no_zero=False):
    # If make_local_only is True don't create a remote host file
    if make_local_only == True:
        pass
    else:
        # Construct a string that generates a host file with the desired host
        # nametype, followed by the private IP.
        length = len(privaddrs)
        count = []
        for each in list(range(length)):
            if no_zero == True:
                count.append(each+1)
            else:
                count.append(each)
        d = dict(zip(count, privaddrs))
        logging.info('Generating a host file for remote hosts')
        for key, value in d.iteritems():
            logging.info('appending host {0}{1} {2}'.format(nametype, key, value))
            host_file_string = "\n{0} {1}{2}".format(value, nametype, key)
            f = open("tmp_host_file", "a+")
            f.write(host_file_string)
        f.close()
        # If make_local is set, also make a /etc/hosts file for the local host
    if make_local == True:
        logging.info('make-local flag detected, appending a local /etc/hosts \
file which contains public IP addresses')
        # it should be the same, but will set the length/count to the public
        # list
        length = len(pubaddrs)
        count = []
        for each in list(range(length)):
            if no_zero == True:
                count.append(each+1)
            else:
                count.append(each)
        # Buid a different dict for pubaddrs
        t = dict(zip(count, pubaddrs))
        for key, value in t.iteritems():
            logging.info('appending host locally {0}{1} {2}'.format(nametype,
                                                                    key,
                                                                    value))
            host_file_string = "\n{0} {1}{2}".format(value, nametype, key)
            f = open("/etc/hosts", "a+")
            try:
                f.write(host_file_string)
            except IOError:
                logging.error('Permission denied.  To use make-local you must \
have root!')
                sys.exit(1)
        f.close()

"""
Copy the remote host files to each host
"""
def copy_host_files(keyfile, user, pubaddrs=public_ips):
    k = paramiko.RSAKey.from_private_key_file(keyfile)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logging.info('Copying host files to remote hosts')
    # Use a specific user to connect
    # This provides support for additional users outside of the docker lab
    logging.info('Using user {0} to connect'.format(user))
    for each in pubaddrs:
        logging.info('copying host file to {0}'.format(each))
        ssh.connect(
                    each,
                    username="{0}".format(user),
                    pkey=k
                    )
        scp = SCPClient(ssh.get_transport())
        scp.put("tmp_host_file", "/home/{0}/hosts".format(user))
        # Append the newly created hostfile into the existing hosts file on
        # each host
        ssh.exec_command("sudo bash -c 'cat /home/{0}/hosts >> /etc/hosts'".format(user))
        # cleanup tmp file remotely
        ssh.exec_command("rm -f /home/{0}/hosts".format(user))
    logging.info('All host files copied to remote hosts')

"""
Cleanup
"""
def cleanup_tmp(tmpfile='tmp_host_file'):
    logging.info('Cleaning up temporary files')
    os.remove(tmpfile)

def main():
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
                        directory).")
    parser.add_argument("-f",
                        dest="env_file",
                        help="Specify the location/name of the environment.txt \
                        file found inside of your train directory.  This is \
                        used to read IP's of the hosts.",
                        required=True)
    parser.add_argument("-u",
                        "--user",
                        dest="user",
                        help="Override the default user used to connect.  Use \
                        this flag if you've deployed an environment that is \
                        not based on the 'docker' lab to override the default \
                        user AWS creates for login.")
    parser.add_argument("--make-local",
                        dest="make_local",
                        action="store_true",
                        help="Add entries to the hosts in your local \
                        /etc/hosts file (requires root) using the public IP's \
                        for each host.")
    parser.add_argument("--make-local-only",
                        dest="make_local_only",
                        action="store_true",
                        help="Same behavior as --make-local without remote \
                        edits to host files.  Should be used in place of \
                        --make-local.")
    parser.add_argument("--no-zero",
                        dest="no_zero",
                        action="store_true",
                        help="Do not start hostname count from 0, start from \
                        1 instead.  For example, with --no-zero hosts will \
                        be named 'docker1, docker2, etc.'  By default host \
                        naming will follow the train.env naming convention \
                        which is 'docker0, docker1, etc.'")
    parser.add_argument("-D",
                        "--debug",
                        dest="debug",
                        action="store_true",
                        help="Enable debugging")


    args = parser.parse_args()

    # logging
    if args.debug == False:
        logger = logging.getLogger(name=None)
        logging.basicConfig(format='%(levelname)s: %(message)s',
                            level=logging.INFO
                            )
    else:
        logger = logging.getLogger(name=None)
        logging.basicConfig(format='%(levelname)s: %(message)s',
                            level=logging.DEBUG
                            )

    # Ensure that both make-local flags are not passed
    if args.make_local and args.make_local_only == True:
        logging.error('Use either --make-local or --make-local-only, not both!')
        sys.exit(1)

    # Check for root early if make-local is used
    if args.make_local or args.make_local_only == True:
        if not os.geteuid() == 0:
            logging.error('You must be root to use the make-local flag!')
            sys.exit(1)

    # Check for ssh identity file
    if args.make_local_only != True:
        if args.ssh_identity_file == None:
            logging.error("""usage: make_host_file.py [-h] [-N NAMETYPE]
-i SSH_IDENTITY_FILE -f ENV_FILE [-u USER] [--make-local] [--no-zero] [-D]
argument -i is required.
"""
            )
            sys.exit(1)

    # Generate host list
    env_file = expand_homedir(args.env_file)
    host_list(env_file)

    # If no user is given assume ubuntu, else set per flag
    if args.user == None:
        user = 'ubuntu'
    else:
        user = args.user

    # Get default nametype
    if args.nametype == None:
        nametype = get_nametype(env_file)
    else:
        logging.info('-N detected, using user set nametype')
        nametype = args.nametype

    # announce the nametype we'll use
    logging.info("Will use name: {0}".format(nametype))

    # Generate host files, cleanup and exit for make-local-only
    if args.make_local_only == True:
        logging.info("--make-local-only detected. Creating local hosts file \
entries only!")
        generate_host_file(nametype, make_local=True, make_local_only=True,
                           no_zero=args.no_zero)
        logging.info("All tasks complete.")
        sys.exit(0)

    # Generate a hosts file
    if args.make_local == True:
        generate_host_file(nametype, make_local=True, no_zero=args.no_zero)
    else:
        generate_host_file(nametype, no_zero=args.no_zero)

    # Copy remote hosts
    copy_host_files(args.ssh_identity_file, user)

    # Cleanup tmp_host_file used for remote host editing
    cleanup_tmp()

    # Tell users we're done
    logging.info("All tasks complete.")

"""
Main
"""
if __name__ == '__main__':
    sys.exit(main())
