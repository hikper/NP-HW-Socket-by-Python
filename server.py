from database import UserData
from board import *
import socket
import sys
import os
import threading
import argparse
import random

#### arg parse 
#### run by using puthon3 server.py <host> <port>
host = "127.0.0.1"      #default host
port = 49155            #default port
argp = argparse.ArgumentParser()
argp.add_argument("port")
args = argp.parse_args()
port = int(args.port)
print(f"Server host: {host}, port: {port}")

#### random generate num
randomdict = dict()

#### chatroom_dict
chatroom_dict = dict()



class BBS_sever(threading.Thread):
    def __init__(self, client, address):
        threading.Thread.__init__(self)
        self.client = client
        self.address = address
        print(f"New connection {self.address}")
        self.db = UserData()
        self.username = ""
        self.email = ""
        self.password = ""
        self.rannum = ""

    def run(self):
        welcome_message = "********************************\n** Welcome to the BBS server. **\n********************************"
        self.client.send(welcome_message.encode())
        try:
            while True:
                cmd = self.client.recv(1024).decode()
                # print("From "+str(self.address)+" received message : "+cmd)
                response = self.response(cmd, self.client)
                self.client.send(response.encode())
                if response == "exit":
                    self.client.close()
                    break
        except (ConnectionResetError,ConnectionAbortedError,BrokenPipeError):
            print(f"Client {str(self.address)} shut down unexceptedly.")
            self.client.close()

    def response(self, cmd, client):
        if cmd == "":
            return "400 Error Bad request!"
        raw = cmd
        cmd = cmd.split(" ")
        if  len(cmd) == 0:
            return f"Unable to recognize {str(len(cmd))}"
        elif cmd[0] == "login":
            try:
                username = cmd[1]
                password = cmd[2]
            except:
                return "Usage: login <username> <password>"

            check = self.db.find_username(username)
            if self.username != "":
                return "Please logout first."
            elif check is not None and  password == check[2]:
                self.username = username
                self.password = password
                self.rannum = self.insert_randomlist(username)
                return f"Welcome, {self.username}${self.rannum}"
            else:
                return "Login failed."

        elif cmd[0] == "logout":
            if self.username == "":
                return "Please login first."
            elif chatroom_dict.get(self.username) != None and chatroom_dict[self.username][3] == "open":
                return "Please do “attach” and “leave-chatroom” first."
            else:
                username = self.username
                self.username = ""
                self.email = ""
                self.password = ""
                randomdict.pop(self.rannum, None)
                self.rannum = ""
                return f"Bye, {username}"
        elif cmd[0] == "list-user":
            data = self.db.print()
            ret = "{:<12s}{:<12s}".format("Name","Email")+"\n"
            for item in data:
                ret += "{:<12s}{:<12s}".format(item[0],item[1])+"\n"
            return ret
        elif cmd[0] == "create-board":
            try:
                name = cmd[1]
            except (AttributeError,IndexError):
                return "Usage: create-board <name>"
            return create_board(name,self.username)
        elif cmd[0] == "create-post":
            return create_post(raw,self.username)
        elif cmd[0] == "list-board":
            return list_board()
        elif cmd[0] == "list-post":
            try:
                board = cmd[1]
            except (AttributeError,IndexError):
                return "Usage: list-post <board-name>"
            return list_post(board)
        elif cmd[0] == "read":
            try:
                sn = int(cmd[1])
            except (AttributeError,IndexError):
                return "Usage: read <post-S/N>"
            return read_post(sn)
        elif cmd[0] == "delete-post":
            try:
                sn = int(cmd[1])
            except (AttributeError,IndexError):
                return "Usage: delete-post <post-S/N>"
            return delete_post(sn,self.username)
        elif cmd[0] == "update-post":
            try:
                sn = int(cmd[1])
            except (AttributeError,IndexError):
                return "Usage: update-post <post-S/N> --title/content <new>"
            return update_post(sn,self.username,raw)
        elif cmd[0] == "comment":
            try:
                sn = int(cmd[1])
            except (AttributeError,IndexError):
                return "Usage: comment <post-S/N> <comment>"
            return make_comment(sn,self.username,raw)
        elif cmd[0] == "create-chatroom":
            if self.username == "":
                return "Please login first."
            if chatroom_dict.get(self.username) != None:
                return "User has already created the chatroom."
            try:
                chatroom = [self.username, self.address, cmd[1], "open"]
                chatroom_dict[self.username] = chatroom
            except (AttributeError,IndexError):
                return "Usage: create-chatroom <port>"
            return "start to create chatroom…"+" "+str(self.address[0])+" "+str(cmd[1])
        elif cmd[0] == "list-chatroom":
            if self.username == "":
                return "Please login first."
            ret = "{:<16s}{:<16s}".format("Chatroom_name","Status")
            for key in chatroom_dict:
                ret += "\n"+"{:<16s}{:<16s}".format(chatroom_dict[key][0],chatroom_dict[key][3])
            return ret
        elif cmd[0] == "join-chatroom":
            if self.username == "":
                return "Please login first."
            try:
                chatname = cmd[1]
            except (AttributeError,IndexError):
                return "Usage: join-chatroom <chatroom_name>"
            if chatroom_dict.get(chatname) == None or chatroom_dict[chatname][3] != "open":
                return "The chatroom does not exist or the chatroom is close."
            return "Action: connection to chatroom server. "+str(chatroom_dict[chatname][1][0])+" "+str(chatroom_dict[chatname][2])
        elif cmd[0] == "leave-chatroom":
            chatroom_dict[self.username][3] = "close"
            return "close"
        elif cmd[0] == "restart-chatroom":
            if self.username == "":
                return "Please login first."
            elif chatroom_dict.get(self.username) == None:
                return "Please create-chatroom first."
            elif chatroom_dict[self.username][3] == "open":
                return "Your chatroom is still running."
            chatroom_dict[self.username][3] = "open"
            return "start to create chatroom… "+f"{chatroom_dict[self.username][1][0]} {chatroom_dict[self.username][2]}"
        elif cmd[0] == "exit":
            return "exit"
        else:
            print(f"can not handle cmd {cmd}")
        return "What?"

    def insert_randomlist(self,username):
        rannum = str(random.random())
        while randomdict.get(rannum) != None:
            rannum = str(random.random())
        randomdict[rannum] = username
        return rannum

class UDP_server(threading.Thread):
    def __init__(self,host,port):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((host, port))
        self.db = UserData()
    def run(self):
        while True:
            cmd,address = self.s.recvfrom(1024)
            cmd = cmd.decode()
            print(f"form {address}: {cmd}")
            self.s.sendto(self.response(cmd).encode(),address)
    def response(self,cmd):
        cmd = cmd.split(" ")
        if len(cmd) == 0:
            return "Bad request"
        elif cmd[0] == "register":
            try:
                username = cmd[1]
                email = cmd[2]
                password = cmd[3]
                if self.db.create_new_user(username,email,password) is True:
                    return "Register successfully."
                else:
                    return "Username is already used."
            except:
                return "Usage: register <username> <email> <password>"
        elif cmd[0] == "whoami":
            if len(cmd) < 2:
                return "error!"
            rannum = cmd[1]
            if randomdict.get(rannum) != None:
                return randomdict[rannum]
            else :
                return "Please login first."
        return "UDP WHAT!"+str(cmd)
                




def main():
    UDP_server(host,port).start()

    # print("UDP Server ready.")
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    s.bind((host, port))
    s.listen(20)
    # print("TCP Server start to run.")
    print("Server ready.")

    while True:
        client, addr = s.accept()
        BBS_sever(client, addr).start()

if __name__ == "__main__":
    main()
