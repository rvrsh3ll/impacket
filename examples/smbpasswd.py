#!/usr/bin/env python
#
# SECUREAUTH LABS. Copyright 2018 SecureAuth Corporation. All rights reserved.
#
# This software is provided under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# Description:
#  This script is an alternative to smbpasswd tool for changing Windows
#  passwords over SMB (MSRPC-SAMR) remotely from Linux with a single shot to
#  SamrUnicodeChangePasswordUser2 function (Opnum 55).
#
# Author:
#  Sam Freeside (@snovvcrash)
#
# Example:
#  python smbpasswd.py 'j.doe:Passw0rd!'@pc1.megacorp.local
#  python smbpasswd.py 'j.doe:Passw0rd!'@10.10.13.37 -newpass 'N3wPassw0rd!'
#
# References:
#  https://github.com/samba-team/samba/blob/master/source3/utils/smbpasswd.c
#  https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-samr/acb3204a-da8b-478e-9139-1ea589edb880

import sys
from getpass import getpass
from argparse import ArgumentParser

from impacket.dcerpc.v5 import transport, samr


def connect(host_name_or_ip):
	rpctransport = transport.SMBTransport(host_name_or_ip, filename=r'\samr')
	if hasattr(rpctransport, 'set_credentials'):
		rpctransport.set_credentials(username='', password='', domain='', lmhash='', nthash='', aesKey='') # null session

	dce = rpctransport.get_dce_rpc()
	dce.connect()
	dce.bind(samr.MSRPC_UUID_SAMR)

	return dce


def hSamrUnicodeChangePasswordUser2(username, currpass, newpass, target):
	dce = connect(target)

	try:
		resp = samr.hSamrUnicodeChangePasswordUser2(dce, '\x00', username, currpass, newpass)
		#resp.dump()
	except Exception as e:
		if 'STATUS_WRONG_PASSWORD' in str(e):
			print('[-] Current SMB password is not correct.')
		elif 'STATUS_PASSWORD_RESTRICTION' in str(e):
			print('[-] Some password update rule has been violated. For example, the password may not meet length criteria.')
		else:
			raise e
	else:
		print('[+] Password was changed successfully.')


def parse_target(target):
	try:
		userpass, hostname_or_ip = target.rsplit('@', 1)
	except ValueError:
		print('Wrong target string format. For more information run with --help option.')
		sys.exit(1)

	try:
		username, currpass = userpass.split(':', 1)
	except ValueError:
		username = userpass
		currpass = getpass('Current SMB password: ')

	return (username, currpass, hostname_or_ip)


if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('target', help='<username[:currpass]>@<target_hostname_or_IP_address>')
	parser.add_argument('-newpass', default=None, help='new SMB password')
	args = parser.parse_args()

	username, currpass, hostname_or_ip = parse_target(args.target)

	if args.newpass is None:
		newpass = getpass('New SMB password: ')
		newpass_verify = getpass('Retype new SMB password: ')
		if newpass != newpass_verify:
			print('[-] Password does not match, try again.')
			sys.exit(2)
	else:
		newpass = args.newpass

	hSamrUnicodeChangePasswordUser2(username, currpass, newpass, hostname_or_ip)
