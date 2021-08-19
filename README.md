# Project: Interest Groups
We implement a command-line network application that supports interest-based discussion groups using the Internet domain sockets. The database is stored in a SQL file.

1. Files description:

* client.py: implement client-side handling  
* server.py: implement server-side handling
* server.db: Database file

2. Building a single-server system

All discussion groups are hosted at a single server. All users access this single server to participate in discussion groups. Each user has a unique user ID. Each discussion group has a unique group ID and a unique group name.  Each user post has a unique post ID, a subject line, and a content body. Each post is also associated with the user ID of the post author as well as a time stamp denoting when the post is submitted.

The server is started first and waits at a known port for requests from clients. The port number that the server listens at can be hard-coded, or can be output to the standard output from your program and used when starting client programs. The client program takes two command line arguments: (i) the name of the machine on which the server program is running, (ii) the port number that the server is listening at.

3. Logging commands

* login – this command takes one argument, your user ID. It is used by the application to determine which discussion groups you have subscribed to, and for each subscribed group, which posts you have read.  For simplicity, we do not prompt the user for a password and skip the authentication process.

* help – this command takes no argument. It prints a list of supported commands and sub-commands. For each command or sub-command, a brief description of its function and the syntax of usage are displayed.

4. Once a user is logged in, many commands for a discussion groups are supported. Details of these commands are given in commands_description
