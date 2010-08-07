#!/usr/bin/python

from subprocess import Popen, PIPE
import tempfile
import sys
import re
import select
from time import strftime, time
import datetime
import math
import os
import string

## CONFIGURATION START ##
SERVER             = "./minecraft_server.jar"
ADMINS             = ['Flippeh']
HEAPMEM_MAX        = "1024M"
HEAPMEM_MIN        = "1024M"
MAXPLAYER          = 10
VOTEKICK_THRESHOLD = 80 # = 80%
## CONFIGURATION END ##
# modify if you know what you're doing, better not otherwise :)

print "[SRVBOT] Starting..."
print "[SRVBOT] Running the server executable..."

server_args = ["java", "-Xmx%s" % (HEAPMEM_MAX), "-Xms%s" % (HEAPMEM_MIN), 
               "-jar", SERVER, "nogui"]

if os.name == "nt":
   import win32pipe
   (stdin, stdout) = win32pipe.popen4(" ".join(server_args))

else:
   server = Popen(server_args,
                  stdout = PIPE,
                  stdin = PIPE,
                  stderr = PIPE)
   outputs = [server.stderr, server.stdout]
   stdin = server.stdin

# Proudly scraped off http://copy.bplaced.net/mc/ids.php
blocks = dict({
   "air": 0, "rock": 0, "grass": 2, "dirt": 3, "cobblestone": 4, "wood": 5,
   "sapling": 6, "bedrock": 7, "water": 8, "stillwater": 9, "lava": 10,
   "stilllava": 11, "sand": 12, "gravel": 13, "goldore": 14, "ironore": 15,
   "coalore": 16, "tree": 17, "leaves": 18, "sponge": 19, "glass": 20,
   "sapling": 6, "bedrock": 7, "water": 8, "stillwater": 9, "lava": 10,
   "stilllava": 11, "sand": 12, "gravel": 13, "goldore": 14, "ironore": 15,
   "coalore": 16, "tree": 17, "leaves": 18, "sponge": 19, "glass": 20,
   "cloth": 35, "flower": 37, "rose": 38, "brown": 39, "red": 40, "goldblock": 41,
   "ironblock": 42, "double": 43, "stair": 44, "brickblock": 45, "tnt": 46, 
   "bookshelf": 47, "mossy": 48, "obsidian": 49, "torch": 50, "fire": 51,
   "mob": 52, "wood": 53, "chest": 54, "redstone": 55, "diamond": 56,
   "diamondblock": 57, "workbench": 58, "crop": 59, "soil": 60, "furnace": 61,
   "lit": 62, "sign": 63, "wood": 64, "ladder": 65, "rails": 66, 
   "stonestairs": 67, "sign": 68, "lever": 69, "rock": 70, "irondoor": 71, 
   "wood": 72, "redstoneore1": 73, "redstoneore2": 74, "redstonetorch1": 75,
   "redstonetorch2": 76, "button": 77, "snow": 78, "ice": 79, "snowblock": 80,
   "cactus": 81, "clayblock": 82, "reedblock": 83, "jukebox": 84, 
   
   "ironshovel": 256, "ironpick": 257, "ironaxe": 258, "flintsteel": 259,
   "apple": 260, "bow": 261, "arrow": 262, "coal": 263, "diamond": 264,
   "iron": 265, "gold": 266, "ironsword": 267, "woodsword": 268, 
   "woodshovel": 269, "woodpick": 270, "woodaxe": 271, "stonesword": 272,
   "stoneshovel": 273, "stonepick": 274, "stoneaxe": 275, "diamondsword": 276,
   "diamondshovel": 277, "diamondpick": 278, "diamondaxe": 279, "stick": 280,
   "bowl": 281, "soup": 282, "goldsword": 283, "goldshovel": 284, 
   "goldpick": 285, "goldaxe": 286, "string": 287, "feather": 288, 
   "gunpowder": 289, "woodhoe": 290, "stonehoe": 291, "ironhoe": 292,
   "diamondhoe": 293,"goldhoe": 294, "seeds": 295, "wheat": 296, "bread": 297,
   "leatherhelmet": 298, "leatherchest": 299, "leatherpants": 300,
   "leatherboots": 301, "chainmailhelmet": 302, "chainmailchest": 303,
   "chainmailpants": 304, "chainmailboots": 305, "ironhelmet": 306,
   "ironchest": 307, "ironpants": 308, "ironboots": 309, "diamondhelmet": 310,
   "diamondchest": 311, "diamondpants": 312, "diamondboots": 313,
   "goldhelmet": 314, "goldchest": 315, "goldpants": 316, "goldboots": 317,
   "flint": 318, "meat": 319, "cookedmeat": 320, "painting": 321, 
   "goldenapple": 322, "sign": 323, "wooddoor": 324, "bucket": 325,
   "waterbucket": 326, "lavabucket": 327, "minecart": 328, "saddle": 329,
   "irondoor": 330, "redstonedust": 331, "snowball": 332, "boat": 333,
   "leather": 334, "milkbucket": 335, "brick": 336, "clay": 337, "reed": 338,
   "paper": 339, "book": 340, "slimeorb": 341, "storagecart": 342, 
   "poweredcart": 343, "egg": 344
})

# Prepare some regexps
# To add multiple admins, you can separate them with a pipe:
# admin = re.compile('Flippeh|Somedude|Anotherdude')

admin = re.compile(string.join(ADMINS, "|"), re.IGNORECASE)

chatmessage = re.compile('^\d.+ \d.+ .INFO. <(.+?)> (.+)$')

srv_list_response = re.compile('Connected players: (.+)')
srv_playercount   = re.compile('^Player count: (\d+)')
srv_join          = re.compile('^\d.+ \d.+ .INFO. (.+?) \[.+?\] logged in')
srv_part          = re.compile('^\d.+ \d.+ .INFO. (.+?) lost connection')

try:
   current_players = 0
   started         = int(time())
   votekicks       = dict({})
   players         = dict({})

   motd            = ["Welcome $nick!", 
                      "Type \"!help\" to see the available commands."]
   
   temp_admins     = []
   
   if os.path.exists("server.bans"):
      try:
         bans = open("server.bans", 'r')
         ban_list = map(lambda x: x.rstrip(), bans.readlines()) # more magic!

      except:
         print "[SRVBOT] Error while loading bans! Gotta continue with them"
      finally:
         bans.close()

   else:
      try:
         print "[SRVBOT] No ban file, creating it..."
         bans = open("server.bans", 'w')

      except:
         print "[SRVBOT] Error creating 'server.bans'"
      finally:
         bans.close()

      ban_list = []

   # main loop
   while True:
      try:
         if os.name == 'nt':
            outready = [stdout]
         else:
            outready, inready, exceptready = select.select(outputs, [], [])
      except:
         break

      for s in outready:
         line = s.readline().rstrip()
      
         if line == "":
            break

         print "[SERVER] %s" % (line)

         chat = chatmessage.match(line)
         if chat:
            nick = chat.group(1)
            text = chat.group(2)

            parts = text.split(" ")

            if parts[0] == "!give":
               if (admin.match(nick) or nick.lower() in temp_admins):
                  try:
                     item = parts[3]
                     amount = parts[2]
                     target = parts[1]
   
                     if not amount.isdigit():
                        stdin.write("say Amount must be a number!\n")
                        continue

                     if not item.isdigit():
                        try:
                           item = blocks[item]
                        except KeyError:
                           stdin.write("say No such ID\n")
                           continue

                     for i in range(int(parts[2])):
                        stdin.write("give %s %s\n" 
                              % (parts[1], item))
                  except IndexError:
                     stdin.write("say Syntax: !give <player> <amount> <what>\n")
               else:
                  stdin.write("say You're no admin, %s!\n" % (nick))

            elif parts[0] == "!stop":
               if (admin.match(nick)):
                  stdin.write("stop\n")
               else:
                  stdin.write("say You're no admin, %s!\n" % (nick))

            elif parts[0] == "!giveall":
                if (admin.match(nick)):
                    try:
                        item = parts[2]
                        amount = parts[1]

                        if not amount.isdigit():
                            stdin.write("say Amount must be a number!\n")
                            continue

                        if not item.isdigit():
                            try:
                                item = blocks[item]
                            except KeyError:
                                stdin.write("say No such ID\n")
                                continue

                        for target in players:
                            for i in range(int(amount)):
                                stdin.write("give %s %s\n" % (target, item))
                    except IndexError:
                        stdin.write("say Syntax: !giveall <amount> <what>\n")
                else:
                    stdin.write("say You're no admin, %s!\n" % (nick))
			   	     	
            elif parts[0] == "!lite":
               if (admin.match(nick)):
                  try:
                     target = parts[1]

                     if not target.lower() in temp_admins:
                        temp_admins.append(target.lower())
                        stdin.write("say Made %s lite admin\n" % (target))
                     else:
                        stdin.write("say Player already is an admin\n")
                  except IndexError:
                     stdin.write("say Syntax: !lite <player>\n")
               else:
                  stdin.write("say You're no admin, %s!\n" % (nick))

            elif parts[0] == "!unlite":
               if (admin.match(nick)):
                  try:
                     target = parts[1]

                     if target.lower() in temp_admins:
                        temp_admins.remove(target.lower())
                        stdin.write("say Removed %s's admin\n" % (target))
                     else:
                        stdin.write("say No such admin\n")
                  except IndexError:
                     stdin.write("say Syntax: !unlite <player>\n")
               else:
                  stdin.write("say You're no admin, %s!\n" % (nick))

            elif parts[0] == "!kick":
               if (admin.match(nick) or nick in temp_admins):
                  try:
                     target = parts[1]
                     stdin.write("kick %s\n" % (target))
                  except IndexError:
                     stdin.write("say Syntax: !kick <player>\n")
               else:
                  stdin.write("say You're no admin, %s!\n" % (nick))

            elif parts[0] == "!ban":
               if (admin.match(nick) or nick.lower() in temp_admins):

                  try:
                     target = parts[1].lower()
                     
                     if target in ban_list:
                        stdin.write("say Player '%s' already banned\n" %
                              target)
                     else:
                        ban_list.append(target)

                        try:
                           bans = open('server.bans', 'w')
                           for nick in ban_list:
                              bans.write("%s\n" % nick)
   
                           bans.close()
   
                           stdin.write("say Banned player '%s'\n" 
                                 % target)
                        except:
                           stdin.write("say MAJOR OOPSIE!\n")
                  except IndexError:
                     stdin.write("say Syntax: !ban <player>\n")
                     continue
               else:
                  stdin.write("say You're no admin, %s!\n" % (nick))
            
            elif parts[0] == "!unban":
               if (admin.match(nick) or nick.lower() in temp_admins):

                  try:
                     target = parts[1].lower()

                     if target in ban_list:
                        ban_list.remove(target)

                        try:
                           bans = open('server.bans', 'w')
                     
                           for n in ban_list:
                              bans.write("%s\n" % n)

                           bans.close()
                        except:
                           stdin.write("say MAJOR OOPSIE\n")

                        stdin.write("say Removed '%s' from banlist\n" 
                              % target)
                     else:
                        stdin.write("say Player not banned\n")
                  except IndexError:
                     stdin.write("say Syntax: !unban <player>\n")
                     continue

               else:
                  stdin.write("say You're no admin, %s!\n" % (nick))

            elif parts[0] == "!who":
               stdin.write("list\n")

            elif parts[0] == "!time":
               t = strftime("%H:%M:%S (%Z)")
               stdin.write("say The current server time is: %s\n" % (t))

            elif parts[0] == "!votekick":
               voter  = nick

               try:
                  target = parts[1].lower()

                  if admin.match(target) or nick in temp_admins:
                     stdin.write("say You can't votekick admins!\n")
                     continue
               
                  try:
                     if voter in votekicks[target]:
                        stdin.write("say You can't vote twice\n")
                     else:
                        votekicks[target].append(voter)
                  except KeyError:
                     votekicks[target] = [voter]

                  perc = float(len(votekicks[target])) * 100 / current_players
            
                  stdin.write("say Voting to kick %s: %.2f%% / %.2f%%\n" 
                        % (target, perc, VOTEKICK_THRESHOLD))

                  if perc >= VOTEKICK_THRESHOLD:
                     stdin.write("say Vote passed!\n")
                     stdin.write("kick %s\n" % (target))

                     votekicks.pop(target)
               except IndexError:
                  stdin.write("say Syntax: !votekick <player>\n")

            elif parts[0] == "!motd":
               if (len(parts) == 1):
                  for line in motd:
                     stdin.write("say MOTD: %s\n" % line.replace("$nick", nick))
               elif (admin.match(nick)):
                  try:
                     motd = string.join(parts[1:], " ").split("|")

                     for line in motd:
                        stdin.write("say MOTD: %s\n" % line)
                  except IndexError:
                        stdin.write("say Syntax: !motd <message>\n")
               else:
                  stdin.write("say You're no admin, %s!\n" % nick)

            elif parts[0] == "!help":
               stdin.write("say !time - Get current server time\n")
               stdin.write("say !who  - Show who's running\n")
               stdin.write("say !votekick <nick> Vote to kick someone\n")
               stdin.write("say !uptime - Show server uptime\n")

               if admin.match(nick):
                  stdin.write("say !give <nick> <amount> <Item ID | Name> - Give someone an item\n")
                  stdin.write("say !kick <nick> - Kick someone\n")
                  stdin.write("say !stop - Stop the server\n")
                  stdin.write("say !ban <nick> - Ban someone\n")
                  stdin.write("say !unban <nick> - Unban someone\n")
                  stdin.write("say !lite <nick> - Make someone a lite admin\n")
                  stdin.write("say !unlite <nick> - Remove lite admin status\n")
                  stdin.write("say !motd <message> - set the MOTD\n")
                  stdin.write("say !motd - display the MOTD\n")
               
            elif parts[0] == "!uptime":
               uptime = int(time()) - started

               stdin.write("say The server has been up for %s\n" %
                     (datetime.timedelta(seconds = uptime)))
            elif parts[0] == "!debug":
               print players
               print votekicks
               print temp_admins

         else: #NO chat
            # Server responded with the userlist, parse and spread the news
            who_resp = srv_list_response.search(line)
            if who_resp:
               players_on = who_resp.group(1).split(", ")
               stdin.write("say Currently online:\n")

               for i in players_on:
                  try:
                     contime = int(time()) - players[i.lower()]
                     connected = datetime.timedelta(seconds = contime)

                     if admin.match(i):
                        stdin.write("say - %s (Admin) [%s]\n" 
                              % (i, connected))
                     elif i.lower() in temp_admins:
                        stdin.write("say - %s (Lite Admin) [%s]\n" 
                              % (i, connected))
                     else:
                        stdin.write("say - %s [%s]\n"
                              % (i, connected))

                  except KeyError:
                     print "[SRVBOT] Unlisted user: %s" % (i)
 
               continue

            # Server told us the player count
            ply_rsp = srv_playercount.search(line)
            if ply_rsp:
               current_players = int(ply_rsp.group(1))
 
               if current_players > MAXPLAYER and not admin.match(last_joined):
                  stdin.write("say Maximum player limit has been reached\n")
                  stdin.write("kick %s\n" % (last_joined))
            
               continue
 
            # Someone joined
            ply_join = srv_join.search(line)
            if ply_join:
               nick = ply_join.group(1)
               last_joined = nick.lower()
 
               if last_joined in ban_list:
                  stdin.write("kick %s\n" % (last_joined))
               else:
                  players[last_joined] = int(time())

                  for line in motd:
                     stdin.write("say MOTD: %s\n" % line.replace("$nick", nick))
  
               continue

            # Someone left
            ply_quit = srv_part.search(line)
            if ply_quit:
               nick = ply_quit.group(1).lower()
               if nick in players:
                  players.pop(nick)

               if nick in votekicks:
                  votekicks.pop(nick)
         
   print "[SRVBOT] Server shut down"


except KeyboardInterrupt:
   print "[SRVBOT] Caught Ctrl-C, sending stop command"
   stdin.write("stop\n")

   print "[SRVBOT] Waiting for server to die"
   server.wait() # wait for it to die
