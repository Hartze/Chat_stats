#TODO: words per message, --> AUTO WORD CLOUD <--, create images (graphs) of the most used emotes
#TODO: Delete logs on SystemExit? maybe?

#USAGE: "python chat_stats.py" or "python chat_stats.py <channel>"

#NOTE: Twitch's IRC doesn't send certain special characters to sockets, so those won't be logged (like some of them here: http://www.umingo.de/doku.php?id=misc:chat_smileys)
#NOTE: This is meant to be done a few times per stream approximately (not like 100 times per stream). So if you start recording the chat, then restart 5 mins later, the old version will be overwritten, but if you start recording the chat then restart the program 2 hours later, it will start recording new logs. The filename represents when the chat recordings were started.
#NOTE: 'rate' is in messages per minute

create_images = True #create images? Need matplotlib for this. Which you should have anyway because it's awesome.
verbose = False
include_emotes = True #include emotes in the words wordcloud?
debug = False #It won't log any information.

import sys
import os
import time
import string
import datetime
import threading
import urllib2
import json
from twitch_chat_listen import listen
if create_images:
    from make_plot import make_plot
try:
    from pass_info import get_password, get_username
except ImportError:
    print "Error loading Twitch password info"
    print "You need to defined pass_info.py with your username and oauth password"

if len(sys.argv) == 1:
    channel = raw_input("Chat to join: ")
else:
    channel = sys.argv[1]
if 'debug' in sys.argv[2:]:
    debug = True

#thanks to http://twitchemotes.com/ :-)
def getEmotes():
    emotelist = [':)',':(',':o',':z','B)',':/',';)',';p',':p',';P',':P','R)','o_O','O_O','o_o','O_o',':D','>(','<3']
    print "loading emotes..."
    normal = json.load(urllib2.urlopen('http://twitchemotes.com/global.json'))
    emotelist.extend(normal.keys())
    print "loaded global emotes. loading sub emotes..."
    subs = json.load(urllib2.urlopen('http://twitchemotes.com/subscriber.json'))
    for channel in subs.keys():
        emotelist.extend(subs[channel]['emotes'].keys())
    print "loaded sub emotes."
    return emotelist

print "Press CTRL+C at any time to end!"
print

emotelist = getEmotes()
emotelist.remove('GG')
emotelist.remove('Gg')

dt = datetime.datetime.now()
d = dt.strftime('%b-%d-%Y')
t = dt.strftime('%H_%M')
dt = dt.strftime('%b-%d-%Y_%I%p')
directory = "logs/" + channel + '/' + dt
if not os.path.exists(directory) and not debug:
    os.makedirs(directory)
print 
if debug:
    print "Debug mode - not writing to any directories"
else:
    print "Writing to " + directory

def open_file(kind, extension='log'):
    filename = ""
    filename += kind+'.'+extension
    file_path = os.path.relpath(directory + '/' + filename)
    return open(file_path, 'w')

files = []
if not debug:
    authors = open_file('authors') #to get the most active users
    messages = open_file('messages') #literal log of the messages - for average message length, etc.
    words = open_file('words') #to get word cloud
    emotes = open_file('emotes') #for emote stats
    rate = open_file('rate', 'csv') #how fast chat is going
    files = [authors, messages, words, emotes, rate]

def isMessage(data):
    return len(data.split('tmi.twitch.tv PRIVMSG #')) > 1

def formatMessage(message):
    #TODO: remove the "action" stuff for "/me"s
    return message.strip().split('\n')[0].split('\r')[0]

num_messages = 0

def log(author, message):
    global num_messages
    num_messages += 1
    if debug:
        return
    message = formatMessage(message)

    #AUTHORS
    authors.write(author + '\n')
    #MESSAGES
    messages.write(message + '\n')
    #WORDS
    for word in message.split(' '):
        if word.isalnum() and (include_emotes or word not in emotelist):
            words.write(word.upper())
            words.write(' ')
    #EMOTES
    for word in message.split(' '):
        if word in emotelist:
            emotes.write(word.split('/')[0].split('7')[0] + '\n')


#http://stackoverflow.com/questions/5179467
def setInterval(interval, times=-1):
    # This will be the actual decorator
    def outer_wrap(function):
        # This will be the function to be called
        def wrap(*args, **kwargs):
            stop = threading.Event()

            # This is another function to be executed
            # in a different thread to simulate setInterval
            def inner_wrap():
                i = 0
                while i != times and not stop.isSet():
                    stop.wait(interval)
                    function(*args, **kwargs)
                    i += 1
            t = threading.Timer(0, inner_wrap)
            t.daemon = True
            t.start()
            return stop
        return wrap
    return outer_wrap


count=0 #minutes since stream start
if not debug:
    rate.write('TIME_START='+t+'\n')
#RATE
@setInterval(60)
def checkTime():
    if debug:
        return
    global count
    global num_messages
    rate.write(str(count)+','+str(num_messages)+'\n')
    count += 1
    for f in files:
        f.flush()
    num_messages = 0

def endProgram():
    if create_images:
        make_plot(channel, dt)
    for f in files:
        f.close()
#TODO: output images and stuff. stats. (aka the main point of this program.)
    sys.exit()

from thread import start_new_thread
def logEvent(x):
    global count
    try:
        s = raw_input(x)
        rate.write('*'+str(count)+'*,'+s+'\n')
        rate.flush()
        print 'Event "' + s + '" logged at ' + datetime.datetime.now().strftime('%I:%M %p') + '.'
        print
    except (EOFError, KeyboardInterrupt, SystemExit):
        print
        print
        print "==================================ENDING PROGRAM================================"
        endProgram()
    start_new_thread(logEvent, (x,))

start_new_thread(logEvent, ('Log an event to mark this timestamp as a notable point in the stream: ',))

def interpret(data):
    if isMessage(data):
        try:
            author = data.split('@')[1].split('.tmi.twitch.tv')[0]
            s = channel + ' :'
            message = s.join(data.split(s)[1:])
            message = filter(lambda x: x in string.printable, message)
            log(author, message)
            if verbose:
                print (author + ' - ' + message).strip()
        except IndexError:
            print
            print 'MALFORMED DATA - ' + data
            print 'MALFORMED DATA - ' + data
            print 'MALFORMED DATA - ' + data
            print
            return

nick = get_username()
PASS = get_password()

print
print "===============================STARTING CHAT INPUT=============================="
checkTime()
listen(channel, nick, PASS, interpret)
print "==================================ENDING_PROGRAM================================"
endProgram()

