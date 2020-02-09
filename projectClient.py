from socket import *
import sqlite3
import sys
import datetime
import re

# convert seconds to a string representing date and time
def _string_time(s):
	return  datetime.datetime.fromtimestamp(float(s)).strftime('%b %d %H:%M:%S')
def _string_time_2(s):
	return  datetime.datetime.fromtimestamp(float(s)).strftime('%a, %b %d %H:%M:%S EST 2016')
	
# check if args are all integers	
def isInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

def check_int_args(args, start = 1):
	for i in range(start, len(args)):
				if not isInt(args[i]): 
					print 'Invalid arguments \n'
					return False
	return True

# Important: data is stored as a stack.
# read messages from socket with delimiter and store result in an array.
def _readData(sock, buff_size, delim):
	result = []
	data = sock.recv(buff_size).decode()
	while data.find(delim) != -1:
		line, data = data.split(delim, 1)
		result.append(line)
	return result
	
# PRINT FUNCTION
def _print(next, n, mode, data, new = []):
	if next == True:
		if len(data) > n:
			for i in range(0, n):
				data.pop()
		else:
			if len(new) > 0:
				while len(data) != 0:
					data.pop()
			else:
				print 'No more to display'
				return 1		
		if mode == 'rg':
			# Update new posts to the display post stack
			while len(new) != 0:
				data.append(new.pop(0))
	
	temp = []
	if mode == 'ag':
		for i in range (0, min(n, len(data))):
			e = data.pop()
			temp.append(e)
			print str(i+1) + '. (' + e[2] + ') ' + e[1]
		
	if mode == 'sg':
		for i in range (0, min(n, len(data))):
			e = data.pop()
			# Adding new number of posts, if any
			e_new_post = 0
			for new_post in new:
				if new_post[0] == e[1]:
					e_new_post = e[2] + new_post[1]
					e = (e[0], e[1], e_new_post)
					break	
			# if num_post = 0, print nothing	
			if e[2] == 0:
				num_posts = ' '
			else:
				num_posts = str(e[2])
			print str(i+1) + '. ' + num_posts + '  ' + e[1]
			
			temp.append(e)
			
	if mode == 'rg':
		for i in range (0, min(n, len(data))):
			e = data.pop()
			temp.append(e)
			print str(i+1) + '. ' + e[3] + '  ' + _string_time(e[2]) + '    ' + e[1]
			
	if mode == 'rgv':
		for i in range (0, min(n, len(data))):
			e = data.pop()
			temp.append(e)
			print e
	
	while len(temp) != 0:
		data.append(temp.pop())
		
	return 0
	
# ag sub-commands handlers
# data is an array of (groupId, groupName, subOrNot)
def _ag(data, n, conn):
	while 1:
		cmd = raw_input()
		cmds = cmd.split()
		if cmd == 'q':
			#quit from ag command mode
			print 'Quitting from ag mode\n'
			break
		elif cmd == "help":
			print ("Available commands:\n"
				   "  s <num>\tSubscribe to group number <num>\n"
				   "  u <num>\tUnsubscribe from group number <num>\n"
				   "  n\tList the next %d posts, and quits once all posts have been displayed\n"
				   "  q\tQuit from ag mode" % n)
			
		elif cmd == 'n':
			# Print the next n line
			if _print(True, n, 'ag', data) == 1:
				print ('Quitting from ag mode')
				break
		
		elif cmds[0] == 's' or cmds[0] == 'u':
			if len(cmds) >= 2 and cmds[0] == 's':
				# If all argument are integers, insert indicated groups into user history
				if check_int_args(cmds):
					cur = conn.cursor()
					for i in range(1, len(cmds)):
						k = len(data) - int(cmds[i])
						if k < len(data) and k >= 0:
							cur.execute('insert or replace into group_subs values (?, ?, ?)'
								, (data[k][0], data[k][1], 0,))
					# Saving the changes
					conn.commit()
				
			elif len(cmds) >= 2 and cmds[0] == 'u':
				# If all argument are integers, delete indicated groups from user history
				if check_int_args(cmds):
					cur = conn.cursor()
					for i in range(1, len(cmds)):
						k = len(data) - int(cmds[i])
						if k < len(data) and k >= 0:
							cur.execute('delete from group_subs where id = ?', (data[k][0],))
					conn.commit()
			else:
				print "Invalid number of arguments for the s and u commands"
		else:
			print cmd + " is not a valid command.  Enter help for a list of valid commands."

# sg sub-commands handlers		
# data is an array of (groupId, groupName, new_num_posts)		
def _sg(data, sock, n, conn, allGroupsSubs):
	while 1:
		cmd = raw_input()
		cmds = cmd.split()
		if cmd == 'q':
			#quit from ag command mode
			print 'Quitting from sg mode\n'
			break
		elif cmd == "help":
			print ("Available commands:\n"
				   "  u <num>\tUnsubscribe from group number <num>\n"
				   "  n\tList the next %d posts, and quits once all posts have been displayed\n"
				   "  q\tQuit from sg mode" % n)
		elif cmd == 'n':
			# Check for update on the number of new posts:
			# Then print the next n lines
			if _sgn(data, n, sock, allGroupsSubs) == 1:
				print ('Quitting from sg mode')
				break
				
		elif cmds[0] == 'u':
			if len(cmds) >= 2:
				# If all argument are integers, delete indicated groups from user history
				if check_int_args(cmds):
					cur = conn.cursor()
					for i in range(1, len(cmds) -1):
						k = len(data) - int(cmds[i-1])
						if k < len(data) and k >= 0:
							cur.execute('delete from group_subs where id = ?', (data[k][0]))
					conn.commit()
			else:
				print "Invalid number of arguments for the u command"
		else:
			print cmd + " is not a valid command.  Enter help for a list of valid commands."

def _sgn(data, n, sock, allGroupsSubs):
	message = 'SGN' + '\r\n'
	for name in allGroupsSubs:
		message += name + '\r\n'
	sock.send(message.encode())
	dataNew = _readData(sock, 4096, '\n')
	sg_new = []
	if len(dataNew) > 0 and dataNew[0] == '200 OK':
		dataNew.pop(0)
		for i in range(0, len(dataNew), 2):
			print str(dataNew[1]) + ' new posts added to ' + dataNew[0]
			sg_new.append((dataNew[0], int(dataNew[1])))
	# Print the next n line
	if _print(True, n, 'sg', data, sg_new) == 1:
		return 1
	return 0

# Handling n subcommand of rg mode
def _rgn(gname, data, n, sock):
	message = 'RGN ' + gname + '\r\n'
	sock.send(message.encode())
	dataNew = _readData(sock, 4096, '\n')
	new = []
	if len(dataNew) > 0 and dataNew[0] == '200 OK':
		dataNew.pop(0)
		for i in range(0, len(dataNew), 3):
			new.append((dataNew[i], dataNew[i + 1], int(dataNew[i + 2]), 'N'))
	# Print the next n line
	if _print(True, n, 'rg', data, new) == 1:
		return 1
	return 0	
		
# data is an array of (postId, postName, timeStamp, readOrNot)
def _rg(gname, data, n, conn, sock, userid):
	while 1:
		cmd = raw_input()
		cmds = cmd.split()
		#quit from ag command mode
		if cmd == 'q':		
			print 'Quitting from rg mode\n'
			break

		elif cmd == "help":
			print ("Available commands:\n"
				   "  <id>\t\tDisplays detail about the post in the displayed list with number <id>\n"
				   "    n\t\tDisplay %d more lines of the post content\n"
				   "    q\t\tQuit displaying the post content\n"
				   "  r [<num>|<range>]\tMarks either post number <num> as read, or all posts within\n"
				   "\t\t\t\t  <range> as read. <range> must be of the format #-#\n"
				   "  n\t\tList the next %d posts, and quits once all posts have been displayed\n"
				   "  p\t\tSubmit a post to the group\n"
				   "  q\t\tQuit from rg mode" % (n, n))

		# n sub-command
		elif cmd == 'n':
			if _rgn(gname, data, n, sock) == 1:
				print ('Quitting from rg mode')
				break
		
		# p sub-command
		elif cmd == 'p':
			print 'Enter the post subject:'
			subject = raw_input()
			author = userid
			content = ''
			print '\nEnter the content of the post: \n'
			while 1:
				line = raw_input()
				if line == '.':
					break
				content += line + '\n'
			message = 'RGP\r\n' + gname + '\r\n' + subject + '\r\n' + author + '\r\n' + content + '\r\n'
			sock.send(message.encode())
			mess = _readData(sock, 4096, '\n')
			if mess[0] == '200 OK':
				print('Your post is received.')
			if _rgn(gname, data, n, sock) == 1:
				print ('Quitting from rg mode')
				break
		
		# id sub-command:
		elif isInt(cmd) and int(cmd) >=1 and int(cmd) <= n:
			print '\nReading mode'
			i = len(data) - int(cmd)
			message = 'RGV ' + data[i][0] + '\r\n'
			sock.send(message.encode())
			post = _readData(sock, 4096, '\r\n')
			print('\nGroup: ' + post[1])
			print('Subject: ' + post[2])
			print('Author: ' + post[3])
			print('Date: ' + _string_time_2(int(post[4])))
			# Printing first n lines of content
			content = post[5].split('\n')
			_print(False, n, 'rgv', content)
			while 1:
				cmd = raw_input()
				if (cmd == 'n'):
					# Printing next n lines of content 		
					if _print(True, n, 'rgv', content) == 1:
						print ('Quitting from reading mode')
						break
				if (cmd == 'q'):
					print('Quitting from reading post mode\n')
					break
		
		# r sub-command
		elif cmds[0] == 'r':
			if len(cmds) == 2:
				cmds = cmds[1].split('-')
				# If all argument are integers, insert indicated groups into user history
				if check_int_args(cmds, 0):
					cur = conn.cursor()
					for i in range(0, len(cmds)):
						k = len(data) - int(cmds[i])
						if k < len(data) and k >= 0:
							# Check if this post has been read before
							cur.execute('select * from post_read where id = ?', (data[k][0],))
							if cur.fetchone() == None:
								# If not, then update number of post read in the group_subs tables			
								cur.execute('select num_read from group_subs where name = ?', (gname,))
								new_num_read = cur.fetchone()[0] + 1
								cur.execute('update group_subs set num_read = ? where name = ?', (new_num_read, gname,))
							# Update post_read
							cur.execute('insert or replace into post_read values (?, ?)', (data[k][0], gname,))
					# Saving the changes
					conn.commit()				
			else:
				print "Invalid number of arguments for the r command"

		else:
			print cmd + " is not a valid command.  Enter help for a list of valid commands."
										
### MAIN FUNCTION FOR HANDLING LOGIN ###

def _login(userid):
	#Connect to the server 
	global clientSocket
	serverName = 'allv25.all.cs.sunysb.edu'
	serverPort = 6292
	clientSocket = socket(AF_INET, SOCK_STREAM)
	clientSocket.connect((serverName,serverPort))
	try:
		# Initialize user history database
		conn = sqlite3.connect(userid + '_history.db')
		cur = conn.cursor()
		# create table group_subs, list of group subscribed by the user
		cur.execute('create table if not exists '
			+ 'group_subs(id text, name text, num_read int, primary key(id))')
		# create table post_read, list of post read by the user
		cur.execute('create table if not exists ' + 
			'post_read(id text, gname text, primary key(id))')
	except sqlite3.Error:
		print 'Problem with database in client computer'
		sys.exit(1)
	print 'Logged in. Please enter the subcommands \n'
	#Get command from command-line
	while 1:
		cmd = raw_input()
		if cmd == 'logout':
			print ('Logging out...')
			clientSocket.close()
			conn.close()
			sys.exit()
		elif cmd == "help":
			print ("Available commands:\n"
					"  ag <N>\t\tList all groups, optional <N> denotes number of groups to show at once\n"
					"  sg <N>\t\tList all subscribed groups, optional <N> denotes number of groups to show at once\n"
					"  rg <name>\tGet more information about subscribed group <name>\n"
					"  help\tDisplays this menu\n"
					"  logout\tLogout")

		cmd2 = cmd
		cmd = cmd.split()

		### HANDLING AG MODE ###
		
		if len(cmd) <= 2 and cmd[0] == 'ag':
			N = 5
			if len(cmd) == 2 and isInt(cmd[1]): 
				N = int(cmd[1])
			# Request the server for a list of all available groups
			message = 'AG\r\n\r\n'
			clientSocket.send(message.encode())
			
			# Get list of available groups (with id and name) from the server
			# data is a list of (groupid, groupname, sub_or_not)
			data, srv_errAG = [], False
			# reading the first line
			dataAG = _readData(clientSocket, 4096, '\n')
			if dataAG[0] != '200 OK':
				print 'Problem from the server'
			else:
				dataAG.pop(0)
				for line in dataAG:			
					parts = line.split()
					cur.execute('select * from group_subs where id = ?', (parts[0],))
					if cur.fetchone() != None:
						subs = 's'
					else:
						subs = ' '
					data.append((parts[0], parts[1], subs))
				data.sort(key = lambda e: e[1], reverse = True)
			# Print the first N groups	
			_print(False, N, 'ag', data)	
			# Handle subcommands in ag mode
			_ag(data, N, conn)
		
		
		### HANDLING SG MODE ###
		
		elif len(cmd) <= 2 and cmd[0] == 'sg':
			N = 5 							# DEFAULT N argument
			if len(cmd) == 2 and isInt(cmd[1]): 
				N = int(cmd[1])
			# Request the server for a list of all available groups
			message = 'SG\r\n'
			result_set = cur.execute('select id from group_subs')
			for rec in result_set:
				message += rec[0] + '\r\n'
			clientSocket.send(message.encode())
			
			# Get list of subscribed groups with id, name and number of posts from the server
			# data is a list of (id, groupname, number of new post)
			data, srv_errSG = [], False
			# list of the name of all group that is subscribed
			allGroupsSubs = []
			dataSG = _readData(clientSocket, 4096, '\n')
			if dataSG[0] != '200 OK':	
				print 'Problem from the server'
			elif len(dataSG) == 1:
				print "There are no subscribed groups to display"
			else:
				dataSG.pop(0)
				for line in dataSG:
					parts = line.split()
					# new post = total posts from server - total num of posts read from user history
					cur.execute('select num_read from group_subs where id = ?', (parts[0],))	
					numPost = int(parts[2]) - cur.fetchone()[0]
					data.append((parts[0], parts[1], numPost))
					allGroupsSubs.append(parts[1])
				data.sort(key = lambda e: e[1], reverse = True)
			# Print the first n groups			
			_print(False, N, 'sg', data)	
			
			# Handle subcommands in sg mode
			_sg(data, clientSocket, N, conn, allGroupsSubs)
				
		## HANDLING RG MODE
		elif len(cmd) >= 2 and len(cmd) <= 3 and cmd[0] == 'rg':
			N = 5
			gname = cmd[1]
			# Check if gname is a subscribed group
			cur.execute('select * from group_subs where name = ?', (gname,))
			if cur.fetchone() == None:
				print 'You haven\'t subscribed group' + gname + '. Quitting from rg mode'
				continue
			
			if len(cmd) == 3 and isInt(cmd[2]):	
				N = int(cmd[2])
			message = 'RG ' + gname + '\r\n'
			clientSocket.send(message.encode())
			dataRG = _readData(clientSocket, 4096, '\r\n')
			if dataRG[0] != '200 OK':	
				print 'Problem from the server'
			else:
				# data is a list of (post_id, post_name, timestamp, read_or_not)
				data = []
				dataRG.pop(0)						
				for line in dataRG:				
					parts = line.split('\n')
					cur.execute('select * from post_read where id = ?', (parts[0],))
					if cur.fetchone() == None:
						read = 'N'
					else:
						read = ' '
					data.append((parts[0], parts[1], int(parts[2]), read))
				data.sort(key = lambda e: (e[3], e[2]))
			# Print the first n groups			
			_print(False, N, 'rg', data)	
			_rg(gname, data, N, conn, clientSocket, userid)

		# print error message
		else:
			print cmd2 + " is not a valid command.  Enter help for a list of available commands"

# Instruct users how to use the commands
def _help():
	print ("Available commands:\n"
			"  login <name>\tLogin with username <name>\n"
		    "  logout\tQuit the program")

# Main
clientSocket = 0
#print ("This is a test: %d\n"
#	   "Tester line 2: %d"% (clientSocket, clientSocket + 1))
while 1:
	cmdLogin = raw_input()
	tmp = cmdLogin.split()
	if cmdLogin == 'help':
		_help()
	elif cmdLogin == "logout":
		break
	elif len(tmp) == 2 and tmp[0] == 'login':
		_login(tmp[1])
	else:
		print cmdLogin + " is not a valid command.  Enter help for a list of available commands"