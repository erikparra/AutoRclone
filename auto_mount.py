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
log_file_name = 'auto_mount.log'

# =================modify here=================


def is_windows():
	return platform.system() == 'Windows'

def parse_args():
	parser = argparse.ArgumentParser(description="Mount remote drive using rclone and merge local and remote mount using mergerfs")
	parser.add_argument('-c', '--config', type=str, required=True, action='store', help='rclone config file')
	parser.add_argument('-r', '--remote', type=str, required=True, help='name of rclone remote drive')
	parser.add_argument('-rp', '--remote-path', type=str, default='/mnt/user/mount_rclone',  help='file path for where to mount rclone drive')
	parser.add_argument('-mp', '--mergerfs-path', type=str, default='/mnt/user/mount_mergerfs', help='file path for where to mount rclone union local storage')
	parser.add_argument('-lp', '--local-path', type=str, default='/mnt/user/mount_local', help='file path for local storage to union')
	parser.add_argument('-l', '--log-path', type=str, default='/mnt/user/auto_mount_config', help='file path for where to store logs and setup scripts')
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
		logging.error('Please install rclone: https://rclone.org/downloads/')
		sys.exit(1)
		#sys.exit('Please install rclone: https://rclone.org/downloads/')
	return ret

def check_mergerfs_program():
	# promote if user has not install mergerfs
	mergerfs_prog = 'mergerfs'
	if is_windows():
		mergerfs_prog += ".exe"
	ret = distutils.spawn.find_executable(mergerfs_prog)
	if ret is None:
		logging.error('Please install mergerfs: https://github.com/trapexit/mergerfs')
		sys.exit(1)
		#sys.exit('Please install rclone: https://github.com/trapexit/mergerfs')
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
			if processName in pinfo['name'] and arg in pinfo['cmdline']:
				listOfProcessObjects.append(pinfo)
		except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
			pass

	return listOfProcessObjects


def check_path(path):
	try:
		os.makedirs(path)
		logging.debug("Directory %s created.", path)
	except FileExistsError:
		logging.debug("Directory %s already exists.", path)


def main():

	args = parse_args()

	# logging setup
	if not os.path.exists(args.log_path):
		os.makedirs(args.log_path)
	logging.basicConfig(
		level=logging.DEBUG,
		format='%(asctime)s %(name)-8s %(levelname)-8s %(message)s',
		handlers=[
			logging.handlers.WatchedFileHandler(os.environ.get("LOGFILE", args.log_path + "/" + log_file_name))])

	logging.info('Auto Mergerfs/Rclone Mount Started.')

	# create paths if don't exists
	check_path(args.remote_path)
	check_path(args.local_path)
	check_path(args.mergerfs_path)

	# if rclone is not installed, quit directly
	rclone_path = check_rclone_program()
	logging.debug('rclone installation detected: %s', rclone_path)

	# if mergerfs is not installed, quit directly
	mergerfs_path = check_mergerfs_program()
	logging.debug('mergerfs installation detected: %s', mergerfs_path)

	if not os.path.isfile(args.config):
		logging.debug('Rclone config file not found: %s', args.config)
		sys.exit(0)

	# checking if rclone already mounted
	is_rclone_mounted = False
	process_list = findProcessIdByName('rclone', 'mount')
	if len(process_list) > 0:
		is_rclone_mounted = True
		logging.debug('Rclone is already running and mounted, PID: %s', process_list[0]['pid'])

	# if remote not mounted, use rclone to mount directory
	if not is_rclone_mounted:
		logging.debug('Creating mount for remote: %s', args.remote)

		# Create rclone mount
		rclone_mount_command = 'nohup rclone mount' \
			' --config {}' \
			' --allow-other' \
			' --buffer-size 256M' \
			' --dir-cache-time 720h' \
			' --drive-chunk-size 512M' \
			' --log-level INFO' \
			' --vfs-read-chunk-size 128M' \
			' --vfs-read-chunk-size-limit off' \
			' --vfs-cache-mode writes ' \
			' {}: {} &'.format(args.config, args.remote, args.remote_path)

		try:
			subprocess.run(rclone_mount_command, shell=True)
			logging.debug('Running rclone mount command: %s', rclone_mount_command)
			time.sleep(3)
		except subprocess.SubprocessError as error:
			logging.exception('Rclone mount command error: %s', str(error))
			sys.exit(1)

		# check if mount successful
		process_list = findProcessIdByName('rclone', 'mount')
		if len(process_list) > 0:
			logging.info('Rclone started and mounted, PID: %s', process_list[0]['pid'])
		else:
			logging.error('Rclone process not found.')

	# check if mergerfs mounted/running
	is_mergerfs_mounted=False
	mergerfs_proc_list = findProcessIdByName('mergerfs', '{}:{}'.format(args.local_path, args.remote_path))
	if len(mergerfs_proc_list) > 0:
		is_mergerfs_mounted=True
		logging.debug('Mergerfs is already running and mounted, PID: %s', mergerfs_proc_list[0]['pid'])

	if not is_mergerfs_mounted:
		logging.debug('Creating mergerfs mount: %s', args.mergerfs_path)

		# create mergerfs mount
		mergerfs_mount_command = 'nohup mergerfs {}:{} {}'.format(args.local_path, args.remote_path, args.mergerfs_path)
		mergerfs_mount_command = mergerfs_mount_command + ' -o rw,noforget,' \
				'use_ino,allow_other,cache.files=off,' \
				'dropcacheonclose=true,async_read=false,func.getattr=newest,' \
				'category.action=all,category.create=ff'


		try:
			subprocess.run(mergerfs_mount_command, shell=True)
			logging.debug('Running mergerfs command: %s', mergerfs_mount_command)
			time.sleep(3)
		except subprocess.SubprocessError as error:
			logging.exception('Mergerfs command error: %s', str(error))
			sys.exit(1)

		# check if mount successful
		mergerfs_proc_list = findProcessIdByName('mergerfs', '{}:{}'.format(args.local_path, args.remote_path))
		if len(mergerfs_proc_list) > 0:
			logging.info('Mergerfs started and mounted, PID: %s', mergerfs_proc_list[0]['pid'])
		else:
			logging.error('Mergerfs process not found.')

	logging.info('Script terminating successfully.')


if __name__ == "__main__":
	main()
