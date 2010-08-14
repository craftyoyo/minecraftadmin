#!/usr/bin/python

import sys
import socket
import select

SERVER = '/home/lukas/listen_me'
PASS   = 'bobblefish'

def waitfor(sock):
   buf = s.recv(128)
   if buf[0] == '+' or buf == '':
      return

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(SERVER)

s.send('%s\r\n' % PASS)

waitfor(s)

if len(sys.argv) > 1:
   s.send('%s\r\n' % sys.argv[1])
   print s.recv(256).rstrip()
   s.send('.close\r\n')
   waitfor(s)
else:
   while True:
      (sout, sin, sexc) = select.select([sys.stdin, s], [], [])
   
      if sout != []:
         for i in sout:
            if i == sys.stdin:
               line = sys.stdin.readline()

               if line == '':
                  s.send('.close\r\n')
                  waitfor(s)

                  s.close()
                  exit()
               else:
                  s.send(line)
            else:
               line = i.recv(512)

               if line == '':
                  s.close()
                  exit()
               else:
                  print line.rstrip()

