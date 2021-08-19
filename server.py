import threading
import socket
import Queue
import sqlite3
import time

def _readData(sock, buff_size, delim):
	result = []
	try:
		data = sock.recv(buff_size).decode()
		while data.find(delim) != -1:
			line, data = data.split(delim, 1)
			result.append(line)
	except Exception:
		print('Connection terminated from client')
	return result

class QueueThread(threading.Thread):
	def __init__(self, q_posts, threads, lock):
		threading.Thread.__init__(self)
		self.q_posts = q_posts
		self.threads = threads
		self.lock = lock
		
	def run(self):
		while True:
			while not self.q_posts.empty():
				new_post = self.q_posts.get()
				with self.lock:
					for thread in self.threads:
						thread.q_in.put(new_post)
						
class ClientThread(threading.Thread):

    def __init__(self,ip,port,clientSocket, q_out):
		# Initialize ClientThread's fields
		threading.Thread.__init__(self)
		self.ip = ip
		self.port = port
		self.sock = clientSocket
		self.q_in = Queue.Queue()
		self.q_out = q_out
		self._tid = "{}:{}".format(ip, port)
		# self.daemon = True
		print ("\nNew thread for "+ ip +":" + str(port))

    def run(self):
		# Create new database connection for this thread
		self.conn = sqlite3.connect('server.db')
		self.cur = self.conn.cursor()
		while True:
			mess = _readData(self.sock, 4096, '\r\n')
			# Handling the case when client program is terminated: to be updated
			if len(mess) == 0:
				print ("\nDeleting thread for "+ self.ip +":" + str(self.port))
				self.conn.close()
				return
			
			# Handling AG message
			if mess[0] == 'AG':
				message = '200 OK\n'
				mess.pop(0)
				self.cur.execute('select id, name from groups')
				for rec in self.cur.fetchall():
					message += str(rec[0]) + ' ' + str(rec[1]) + '\n'
				self.sock.send(message.encode())
			
			# Handling SG message
			elif mess[0] == 'SG':
				message = '200 OK\n'
				mess.pop(0)
				for line in mess:
					self.cur.execute('select id, name, num_posts from groups where id = ?', (int(line),))
					rec = self.cur.fetchone()
					message += str(rec[0]) + ' ' + rec[1] + ' ' + str(rec[2]) + '\n'
				self.sock.send(message.encode())
			
			# Handling SGN message (for timely update)
			elif mess[0] == 'SGN':
				message = ''
				mess.pop(0)
				for gname in mess:
					new_num_post = 0
					while not self.q_in.empty():
						new_post = self.q_in.get()
						if new_post[2] == gname:
							new_num_post += 1
					if new_num_post != 0:
						message += gname + '\n' + str(new_num_post) + '\n'		
				if message == '':
					message = '102 NEW\n'
				else:
					message = '200 OK\n' + message
				self.sock.send(message.encode())
			
			# Handling RG message
			elif mess[0].startswith('RG '):
				message = '200 OK\r\n'
				gname = mess[0].split(' ')[1]
				self.cur.execute('select id, name, timestamp from posts where gname = ?', (gname,))
				for rec in self.cur:
					message += rec[0] + '\n' + rec[1] + '\n' + str(rec[2]) + '\r\n'
				self.sock.send(message.encode())
						
			# Handling RGV message
			elif mess[0].startswith('RGV '):
				message = '200 OK\r\n'
				postId = mess[0].split(' ')[1]
				self.cur.execute('select gname, name, author, timestamp, content from posts where id = ?', (postId,))
				for field in self.cur.fetchone():
					message += str(field) + '\r\n'
				self.sock.send(message.encode())
			
			# Handling RGP message
			elif mess[0] == 'RGP':
				# To be updated
				timestamp = int(time.time())
				# Update number of post for group having new post
				self.cur.execute('select num_posts, id from groups where name = ?', (mess[1],))
				rec = self.cur.fetchone()
				new_num = rec[0] + 1
				groupId = rec[1]
				self.cur.execute('update groups set num_posts = ? where id = ?', (new_num, groupId,))
				# Generate a postID for this group
				postId = str(new_num) + 'g' + str(groupId)
				# Put this new post into databases
				self.cur.execute('insert into posts values (?, ?, ?, ?, ?, ?)',
					(postId, mess[2], mess[1], timestamp, mess[3], mess[4],))
				# Put this new post to post_queue to notify other clients (by client threads)
				self.q_out.put((postId, mess[2], mess[1], timestamp,))
				# Send back confirmation to the client.
				self.sock.send(('200 OK\n' + postId + '\n' + str(timestamp)).encode() + '\n')
				# Saving changes
				self.conn.commit()
				
			# Handling RGN message
			elif mess[0].startswith('RGN '):
				message = ''
				gname = mess[0].split(' ')[1]
				while not self.q_in.empty():
					new_post = self.q_in.get()
					if new_post[2] == gname:
						message += new_post[0] + '\n' + new_post[1] + '\n' + str(new_post[3]) + '\n'			
				if message == '':
					message = '102 NEW\n'
				else:
					message = '200 OK\n' + message
				self.sock.send(message.encode())
			
# Initialize database
conn = sqlite3.connect('server.db')
cur = conn.cursor()
# Create groups table
cur.execute('create table if not exists groups(id int, name text, num_posts int, primary key(id))')
# Create posts table
cur.execute('create table if not exists posts(id text, name text, gname text, timestamp int, author text, '
		 + 'content text, primary key(id))')
conn.close()

### USING QUEUE TO HANDLE POST COMMAND ###
# Queue is used for communication between main thread and client threads
# q.task_done() # Signal that work is done
# q.join() # Wait for all work to be done

threads_lock = threading.Lock()
threads = []
post_queue = Queue.Queue()  # Shared queue for post update (id, name, gname, timestamp)

QueueThread(post_queue, threads, threads_lock).start()

# Main thread for handling incoming connections			
while True:
	host = 'allv25.all.cs.sunysb.edu'
	port = 6292
	tcpSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	tcpSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	tcpSock.bind((host,port))   
	tcpSock.listen(5)
	print ("\nListening for incoming connections...")
	(clientSock, (ip, port)) = tcpSock.accept()
	newthread = ClientThread(ip, port, clientSock, post_queue)
	newthread.start()
	with threads_lock:
		threads.append(newthread)
	