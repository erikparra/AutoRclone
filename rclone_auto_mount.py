# auto rclone
#
# Author Telegram https://t.me/CodyDoby
# Inbox  codyd@qq.com
#
# can copy from
# - [x] publicly shared folder to Team Drive
# - [x] Team Drive to Team Drive
# - [ ] publicly shared folder to publicly shared folder (with write privilege)
# - [ ] Team Drive to publicly shared folder
#   `python3 .\rclone_sa_magic.py -s SourceID -d DestinationID -dp DestinationPathName -b 10`
#
# - [x] local to Team Drive
# - [ ] local to private folder
# - [ ] private folder to any (think service accounts cannot do anything about private folder)
#
from __future__ import print_function
import argparse
import glob
import json
import os, io
import platform
import subprocess
import sys
import time
import distutils.spawn
import psutil
import logging
import logging.handlers
from signal import signal, SIGINT

# =================modify here=================


# =================modify here=================


def is_windows():
	return platform.system() == 'Windows'

def parse_args():
	parser = argparse.ArgumentParser(description="Mount remote drive using rclone and merge local and remote mount using mergerfs")
	parser.add_argument('-c', '--config', type=str, required=True, action='store', help='rclone config file')
	parser.add_argument('-r', '--remote', type=str, required=True, help='name of rclone remote drive')
	parser.add_argument('-rp', '--remote-path', type=str, default='/mnt/user/mount_rclone',  help='file path for where to mount rclone drive')
	parser.add_argument('-mp', '--mergerfs-path', type=str, default='/mnt/user/mount_mergerfs', help='file path for where to mount rclone union local storage')
	parser.add_argument('-lp', '--local-path', type=str, default='/mnt/user/local', help='file path for local storage to union')
	parser.add_argument('-l', '--log-path', type=str, default='/mnt/user/auto_mergerfs_rclone_config', help='file path for where to store logs and setup scripts')
	parser.add_argument('-t', '--test', action='store_true', help='for testing: test script and print debug info')
	parser.add_argument('-o', '--options', type=str, help='comma separated list of rclone options')

	args = parser.parse_args()
	return args

def check_rclone_program():
	# promote if user has not install rclone
	rclone_prog = 'rclone'
	if is_windows():
		rclone_prog += ".exe"
	ret = distutils.spawn.find_executable(rclone_prog)
	if ret is None:
		sys.exit("Please install rclone firstly: https://rclone.org/downloads/")
	return ret

def checkIfProcessRunning(processName):
	'''
	Check if there is any running process that contains the given name processName.
	'''
	# Iterate over the all the running process
	for proc in psutil.process_iter():
		try:
			# Check if process name contains the given name string.
			if processName.lower() in proc.name().lower():
				return True
		except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
			pass
	return False


def findProcessIdByName(processName, arg):
	'''
	Get a list of all the PIDs of a all the running process whose name contains
	the given string processName, and run with arg
	'''

	listOfProcessObjects = []

	# Iterate over the all the running process
	for proc in psutil.process_iter():
		try:
			pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time', 'cmdline'])
			# Check if process name contains the given name string.
			if processName.lower() in pinfo['name'].lower() and arg.lower() in pinfo['cmdline'].lower():
				listOfProcessObjects.append(pinfo)
		except (psutil.NoSuchProcess, psutil.AccessDenied , psutil.ZombieProcess):
			pass

	return listOfProcessObjects


def check_path(path):
	try:
		os.mkdir(path)
		print("Directory ", path, " Created.")
	except FileExistsError:
		print("Directory ", path, " already exists.")


def main():

	args = parse_args()

	#create paths if don't exists
	check_path( args.remote_path )
	check_path( args.local_path )
	check_path( args.mergerfs_path )
	check_path( args.log_path )

	# logging setup
	log = logging.getLogger()
	lhandler = logging.handlers.WatchedFileHandler(os.environ.get("LOGFILE", args.log_path+"/rclone_auto_mount.log"))
	formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
	lhandler.setFormatter(formatter)
	log.addHandler(lhandler)
	log.setLevel(logging.DEBUG)

	# if rclone is not installed, quit directly
	ret = check_rclone_program()
	print("rclone is detected: {}".format(ret))

	if not os.path.isfile(args.config):
		print('Rclone config file not found.')
		sys.exit(0)

	time_start = time.time()
	print("Start: {}".format(time.strftime("%H:%M:%S")))

	if len(findProcessIdByName('rclone', 'mount')) > 0:
		log.debug('rclone mount already mounted. Ending run.')


if __name__ == "__main__":
	main()
