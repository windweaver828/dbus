#!/usr/bin/python

import os
import threading
import Queue
import paramiko
import pickle
import wx
import datetime
from subprocess import Popen, PIPE, STDOUT

PICKLEFILE = os.path.expanduser('~/.clients.p')
CLIENTS = pickle.load(file(PICKLEFILE, 'rb'))

setPos = '$HOME/bin/dbuscontrol setposition'
# duration = str(300)
# position = str(150)


class ThreadedFunction(threading.Thread):
    """
    Thread class that calls a function with arguments
    """
    def __init__(self, func, *args, **kwargs):
        super(ThreadedFunction, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.daemon = True
        self.start()

    def run(self):
        self.func(*self.args, **self.kwargs)

    def finish(self):
        self.join()


class dbusControl(wx.Frame):
    def __init__(self, parent, id, title):
        no_resize = wx.DEFAULT_FRAME_STYLE & ~ \
            (wx.RESIZE_BORDER | wx.RESIZE_BOX | wx.MAXIMIZE_BOX)
        wx.Frame.__init__(self, parent, id, title,
                          size=wx.Size(300, 300),
                          style=no_resize)
        panel = wx.Panel(self, -1, (50, 240))
        self.Q = Queue.Queue()
        self.thread = False
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer, self.timer)
        self.playpause = 0
        self.curpos = 0

        # Creates a blank image to hold movie image
        img = wx.EmptyImage(75, 110)
        self.imageCtrl = wx.StaticBitmap(panel, -1,
                                         wx.BitmapFromImage(img),
                                         (110, 85))

        # Create and position widgets
        self.play = wx.Button(panel, -1, 'Play/Pause', pos=(200, 80))
        self.volup = wx.Button(panel, -1, 'Vol Up',  pos=(200, 110))
        self.voldown = wx.Button(panel, -1, 'Vol Down', pos=(200, 140))
        self.seekbut = wx.Button(panel, -1, 'Seek', pos=(200, 170))
        self.killmovie = wx.Button(panel, -1, 'Stop Movie', pos=(200, 200))
        self.xbmc = wx.Button(panel, -1, 'Open XBMC', pos=(15, 200))
        self.xbmcpass = wx.TextCtrl(panel, -1, size=(85, 25), pos=(15, 230),
                                    style=wx.TE_PASSWORD)
        self.xbmcpass.SetValue("")
        self.closexbmc = wx.Button(panel, -1, "Close XBMC", pos=(15, 260))
        self.mc = wx.Button(panel, -1, 'Movie Control', pos=(105, 200))
        self.mcmovie = wx.TextCtrl(panel, -1, size=(90, 25), pos=(105, 230))
        self.clientbox = wx.ListBox(panel, -1, (22, 85),
                                    (75, 110), CLIENTS.keys())
        self.clienttext = wx.StaticText(panel, -1,
                                        'Available Clients',
                                        (15, 65))
        # StaticTexts with custom font
        self.duration = wx.StaticText(panel, -1,
                                      " No Duration Available ",
                                      pos=(0, 10))
        self.position = wx.StaticText(panel, -1,
                                      " Not Playing ",
                                      pos=(0, 30))
        font = wx.Font(10, wx.DECORATIVE, wx.BOLD, wx.NORMAL)
        self.duration.SetFont(font)
        self.position.SetFont(font)

        # Bind the widgets
        self.play.Bind(wx.EVT_BUTTON, self .pause)
        self.volup.Bind(wx.EVT_BUTTON, self.volUp)
        self.voldown.Bind(wx.EVT_BUTTON, self.volDown)
        self.seekbut.Bind(wx.EVT_BUTTON, self.seek)
        self.killmovie.Bind(wx.EVT_BUTTON, self.stopMovie)
        self.Bind(wx.EVT_LISTBOX, self.onListBox, self.clientbox)
        self.xbmc.Bind(wx.EVT_BUTTON, self.run_xbmc)
        self.closexbmc.Bind(wx.EVT_BUTTON, self.close_xbmc)
        self.mc.Bind(wx.EVT_BUTTON, self.run_movie_control)
        # Rebind global (OS) exit to our exit function
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.threads = list()
        self.time = 3
        self.timer.Start(1000)

    def onClose(self, event):
        for thread in self.threads:
            if thread and thread.isAlive():
                thread.finish()
        self.Destroy()

    # Runs xbmc passing in user and password
    def run_xbmc(self, event):
        user = self.clientbox.GetStringSelection()
        password = self.xbmcpass.GetValue()
        self.xbmcpass.SetValue('')
        if not len(password):
            password = "none"
        cmd = "python /home/james/Programs/XBMC/XBMC.py "+user+" "+password
        Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)

    def close_xbmc(self, event):
        Popen("killall XBMC", shell=True)

    # Plays movie on remote client using
    # Movie controller -m flag (auto play best match)
    def run_movie_control(self, event):
        cmd = "mc -m "
        cmd += self.clientbox.GetStringSelection()+" "
        cmd += self.mcmovie.GetValue()
        Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        self.mcmovie.SetValue('')

    # Resizes image to fit in window
    def scaleBitmap(self, bitmap, width, height):
        return bitmap.Scale(width, height, wx.IMAGE_QUALITY_HIGH)

    def onTimer(self, event):
        if not hasattr(self, 'cli'):
            return
        if self.time >= 5:
            self.time = 0
            self.threads.append(ThreadedFunction(self.refreshStatus))
        else:
            self.time += 1
            if self.curpos:
                self.curpos += 1000000
            position = datetime.timedelta(microseconds=int(self.curpos))
            position = str(position).split(".")[0]
            self.position.SetLabel(" Currently at: "+str(position))
        if not self.Q.empty():
            s = self.Q.get()
            if len(s) == 2:
                duration, position = s
                if not position:
                    position = " Location Not Available"
                self.duration.SetLabel(" Length of movie: "+str(duration))
                self.position.SetLabel(" Currently at: "+str(position))
            elif len(s) == 1:
                s = s[0]
                path = "/".join(s.split("/")[:-1])+"/"
                try:
                    self.getImage(path)
                except:
                    pass
                try:
                    playing = s.split("/")[-2]
                except:
                    playing = "Off"
                    self.curpos = 0
                self.SetTitle(playing)
            else:
                print("Threads likely crashed output from Q is below")
                print("Usually only happens on the first click of the")
                print("Decrease self.time on init to be a few seconds")
                print("less than the reset interval")
                print(s)

    # Sets client, polls client for movie name, duration of movie,
    # current location in movie, path to image, and sets Static text
    # to reflect values
    def onListBox(self, event):
        self.cli = CLIENTS[self.clientbox.GetStringSelection()]
        self.threads.append(ThreadedFunction(self.refreshTitle))

    def refreshStatus(self):
        cmd = '$HOME/bin/dbuscontrol status'
        a = self.sendcmd(self.cli, cmd)
        try:
            duration = a[0].split(':')[1].split("\n")[0]
            position = a[1].split(':')[1].split("\n")[0]
            self.curpos = int(position)
            duration = datetime.timedelta(microseconds=int(duration))
            position = datetime.timedelta(microseconds=int(position))
            duration = str(duration).split(".")[0]
            position = str(position).split(".")[0]
        except:
            duration = ""
            position = ""
        self.Q.put((duration, position))

    def refreshTitle(self):
        self.Q.put(self.sendcmd(self.cli, self.cli['statuscmd']))

    def setClient(self):

        # This is for local
        if self.cli['user'] == 'james':
            cmd = Popen('whatsplaying.py', shell=True, stdin=PIPE,
                        stdout=PIPE, stderr=STDOUT)
            playing = cmd.communicate()[0].strip()
            # playing returns movie path with movie name
            # /media/Ex../Media/Movies/Hey/Hey.mp4
            cmd = 'mediainfo --fullscan ' + playing + \
                  ' | grep -m 3 Duration | cut -d\: -f2 | xargs'
            cmd = Popen(cmd, shell=True, stdin=PIPE,
                        stdout=PIPE, stderr=STDOUT)
            duration = ":".join(cmd.communicate()[0].split(" ")[3:6])
            duration = duration.translate(None, 'hmns')

            # All this is to get duration from mediainfo --fullscan
            # figured how to get back 1:45:15 hour min sec
            position = "Location Not Available"

            # Uses path to image and returns resized image to place in window
            try:
                path = "/"+"/".join(playing.split("/")[:-1])
                self.getImage(path)
            except:
                pass
            try:
                playing = playing.split("/")[-2]
            except:
                playing = "Off"
            # gap = int((21) - (len(playing)/2))
            self.SetTitle(playing)
            if len(duration):
                self.duration.SetLabel("Length of movie: "+str(duration))
                self.position.SetLabel(position)
            else:
                self.duration.SetLabel(" Length of movie: N/A")
                self.position.SetLabel(" Currently at: N/A")

    # Uses movie path to get image and resize it and insert
    # into blank image contrainer we created earlier
    def getImage(self, path):
        if not path == "/":
            for file in os.listdir(path):
                if file.endswith(".jpg"):
                    imagepath = path+"/"+file
            img = wx.Image(imagepath, wx.BITMAP_TYPE_JPEG)
            image = self.scaleBitmap(img, 75, 110)
            # Actually sets the image
            self.imageCtrl.SetBitmap(wx.BitmapFromImage(image))
        else:
            img = wx.EmptyImage(75, 110)
            self.imageCtrl.SetBitmap(wx.BitmapFromImage(img))
        self.Refresh()

    def volUp(self, event):
        if self.cli['user'] == "james":
            cmd = '$HOME/bin/vlcdbus vlc volume $(echo "scale=3; \
                $($HOME/bin/vlcdbus vlc volume)"+.1 | bc)'
        else:
            cmd = '$HOME/bin/dbuscontrol volumeup'
        ThreadedFunction(self.sendcmd, self.cli, cmd)

    def volDown(self, event):
        if self.cli['user'] == "james":
            cmd = '$HOME/bin/vlcdbus vlc volume $(echo "scale=3; \
                    $($HOME/bin/vlcdbus vlc volume)"-.1 | bc)'
        else:
            cmd = '$HOME/bin/dbuscontrol volumedown'
        ThreadedFunction(self.sendcmd, self.cli, cmd)

    def pause(self, event):
        if self.cli['user'] == "james":
            if self.playpause == 0:
                cmd = '$HOME/bin/vlcdbus vlc pause'
                self.playpause += 1
            elif self.playpause == 1:
                cmd = '$HOME/bin/vlcdbus vlc play'
                self.playpause -= 1
        else:
            cmd = '$HOME/bin/dbuscontrol pause'
        ThreadedFunction(self.sendcmd, self.cli, cmd)

    def stopMovie(self, event):
        if self.cli['user'] == 'james':
            cmd = "$HOME/bin/vlcdbus vlc quit"
        else:
            cmd = '$HOME/bin/killmovie'
        ThreadedFunction(self.sendcmd, self.cli, cmd)

    def seek(self, event):
        if self.cli['user'] == "james":
            pass
        else:
            cmd = '$HOME/bin/dbuscontrol seek 120'
            ThreadedFunction(self.sendcmd, self.cli, cmd)

    # Send command via ssh and return output, if any
    def sendcmd(self, cli, cmd):
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(cli['host'], port=cli['port'],
                            username=cli['user'], password=cli['pass'])
        Stdin, Stdout, Stderr = client.exec_command(cmd)
        ret = Stdout.readlines()
        return ret

if __name__ == '__main__':
    app = wx.App()
    frame = dbusControl(None, -1, 'No Title Availabile')
    frame.Show()
    app.MainLoop()
