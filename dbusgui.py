#!/usr/bin/python

import os, paramiko, pickle, wx, datetime
from subprocess import Popen, PIPE, STDOUT
PICKLEFILE = os.path.expanduser('~/.clients.p')
Clients = pickle.load(file(PICKLEFILE, 'rb'))

volUp = '$HOME/bin/dbuscontrol volumeup'
volDown = '$HOME/bin/dbuscontrol volumedown'
setPos = '$HOME/bin/dbuscontrol setposition'
Seek = '$HOME/bin/dbuscontrol seek'
Pause = '$HOME/bin/dbuscontrol pause'
Status = '$HOME/bin/dbuscontrol status'
KillMovie = '$HOME/bin/killmovie'
duration = str(300)
position = str(150)

class dbusControl(wx.Frame):
    def __init__(self, parent, id, title):
        no_resize = wx.DEFAULT_FRAME_STYLE & ~ (wx.RESIZE_BORDER|wx.RESIZE_BOX|wx.MAXIMIZE_BOX)
        wx.Frame.__init__(self, parent, id, title, size=wx.Size(300,300), style = no_resize)
        panel = wx.Panel(self, -1, (50, 240))
        self.Bind(wx.EVT_CLOSE, self.onClose)
        img = wx.EmptyImage(75,110)
        self.imageCtrl = wx.StaticBitmap(panel, wx.ID_ANY, wx.BitmapFromImage(img), (110,85))
        self.play = wx.Button(panel, -1, 'Play/Pause', pos=(200,80))
        self.volup = wx.Button(panel, -1, 'Vol Up',  pos=(200,110))
        self.voldown = wx.Button(panel, -1, 'Vol Down', pos=(200,140))
        self.seekbut = wx.Button(panel, -1, 'Seek', pos=(200,170))
        self.killmovie = wx.Button(panel, -1, 'Stop Movie', pos=(200, 200))
        self.xbmc = wx.Button(panel, -1, 'Open XBMC', pos=(15, 200))
        self.xbmcpass = wx.TextCtrl(panel, -1, size=(85, 25), pos=(15, 230), style=wx.TE_PASSWORD)
        self.closexbmc = wx.Button(panel, -1, "Close XBMC", pos=(15, 260))
        self.xbmcpass.SetValue("")
        self.mc = wx.Button(panel,-1, 'Movie Control', pos=(105,200))
        self.mcmovie = wx.TextCtrl(panel, -1, size=(90, 25), pos=(105, 230))
        clientlist=[]
        for client in Clients.keys ():
            clientlist.append(client)
        self.clientbox = wx.ListBox(panel, -1, (22,85), (75,110), clientlist)
        self.clienttext = wx.StaticText(panel, -1, 'Available Clients', (15,65))
        self.play.Bind(wx.EVT_BUTTON, self .pause)
        self.volup.Bind(wx.EVT_BUTTON, self.volUp)
        self.voldown.Bind(wx.EVT_BUTTON, self.volDown)
        self.seekbut.Bind(wx.EVT_BUTTON, self.seek)
        self.killmovie.Bind(wx.EVT_BUTTON, self.stopMovie)
        self.Bind(wx.EVT_LISTBOX, self.setClient)
        self.xbmc.Bind(wx.EVT_BUTTON, self.run_xbmc)
        self.closexbmc.Bind(wx.EVT_BUTTON, self.close_xbmc)
        self.mc.Bind(wx.EVT_BUTTON, self.run_movie_control)
        self.duration=wx.StaticText(panel, -1, " No Duration Available ", pos=(0,10))
        self.position=wx.StaticText(panel, -1, " Not Playing ", pos=(0,30))
        font = wx.Font(10, wx.DECORATIVE, wx.BOLD, wx.NORMAL)
        self.duration.SetFont(font)
        self.position.SetFont(font)
        
    def onClose(self, event):
        self.Destroy()

    def run_xbmc(self, event):
        user = self.clientbox.GetStringSelection()
        password = self.xbmcpass.GetValue()
        self.xbmcpass.SetValue('')
        if not len(password):
            password = "none"
        cmd = "python /home/james/Programs/XBMC/XBMC.py "+user+" "+password
        Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)

    def close_xbmc(self, event):
        Popen("killall XBMC", shell = True)

    def run_movie_control(self, event):
        client = self.clientbox.GetStringSelection()
        movie = self.mcmovie.GetValue()
        self.mcmovie.SetValue('')
        cmd = "mc -m "+client+" "+movie
        Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        
    def scaleBitmap(self, bitmap, width, height):
        image = bitmap.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
        return image
    
    def setClient(self, event):
        cli = self.clientbox.GetStringSelection()
        self.cli = Clients[cli]
        duration, position = self.statuscmd(self.cli)
        playing=str(self.sendcmd(self.cli, Clients[cli]['statuscmd'])[0])
        if 'Cartoons' in playing:
            playing = playing.replace("/media/Cartoons/", "/media/External-4.0/Media/Lyndas/")  
        path ="/".join(playing.split("/")[:-1])+"/"
        try:
            imageFile = self.getImage(path)
        except: pass
        try:
            playing = playing.split("/")[-2]
        except: playing = "Off"
        gap = int((21) - (len(playing)/2))
        frame.SetTitle(playing)
        if len(duration):
            self.duration.SetLabel("Length of movie: "+str(duration))
            self.position.SetLabel("Currently at: "+str(position))
        else:
            self.duration.SetLabel(" Length of movie: N/A")
            self.position.SetLabel(" Currently at: N/A")

    def getImage(self, path):
        if not path == "/":
            for file in os.listdir(path):
                if file.endswith(".jpg"):
                    imagepath = path+"/"+file
            img = wx.Image(imagepath, wx.BITMAP_TYPE_JPEG)
            image = self.scaleBitmap(img, 75, 110)
            self.imageCtrl.SetBitmap(wx.BitmapFromImage(image))
        else:
            img = wx.EmptyImage(75,110)
            self.imageCtrl.SetBitmap(wx.BitmapFromImage(img))
        self.Refresh() 

    def timecorrect(self, dur, pos):
        duration = datetime.timedelta(microseconds = int(dur))
        position = datetime.timedelta(microseconds = int(pos))
        return duration, position


    def volUp(self, event):
        self.sendcmd(self.cli, volUp)

    def pause(self, event):
        self.sendcmd(self.cli, Pause)
        
    def volDown(self, event):
        self.sendcmd(self.cli, volDown)

    def stopMovie(self, event):
        self.sendcmd(self.cli, KillMovie)
        
    def seek(self, event):
        self.sendcmd(self.cli, Seek+" 120")

    def statuscmd(self, cli, cmd=Status):
        self.client=paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(cli['host'], port=cli['port'], username=cli['user'], password=cli['pass'])
        self.Stdin, self.Stdout, self.Stderr = self.client.exec_command(cmd)
        a = self.Stdout.read().strip()
        try:
            duration = a.split(':')[1].split("\n")[0]
            position = a.split(':')[2].split("\n")[0]
            duration, position = self.timecorrect(duration, position)
            duration = str(duration).split(".")[0]
            position = str(position).split(".")[0]
            self.client.close()
        except:
            duration = ""
            position = ""
        return duration, position
    
    def sendcmd(self, cli, cmd):
        self.client=paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(cli['host'], port=cli['port'], username=cli['user'], password=cli['pass'])
        self.Stdin, self.Stdout, self.Stderr = self.client.exec_command(cmd)
        ret = self.Stdout.readlines()
        return ret

if __name__ == '__main__':
    app = wx.App()
    frame = dbusControl(None, -1, 'No Title Availabile')
    frame.Show()
    app.MainLoop()
