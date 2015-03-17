import os, paramiko, pickle, wx, datetime
PICKLEFILE = os.path.expanduser('~/.clients.p')
Clients = pickle.load(file(PICKLEFILE, 'rb'))

volUp = '/home/pi/bin/dbuscontrol volumeup'#os.path.expanduser('~/bin/dbuscontrol volumeup')
volDown = '/home/pi/bin/dbuscontrol volumedown'#os.path.expanduser('~/bin/dbuscontrol volumedown')
setPos = '/home/pi/bin/dbuscontrol setposition'#os.path.expanduser('~/bin/dbuscontrol setposition ')
Seek = '/home/pi/bin/dbuscontrol seek'#os.path.expanduser('~/bin/dbuscontrol seek')
Pause = '/home/pi/bin/dbuscontrol pause'#os.path.expanduser('~/bin/dbuscontrol pause')
Status = ('/home/pi/bin/dbuscontrol status')
duration = str(300)
position = str(150)

class dbusControl(wx.Frame):
    def __init__(self, parent, id, title):
        no_resize = wx.DEFAULT_FRAME_STYLE & ~ (wx.RESIZE_BORDER|wx.RESIZE_BOX|wx.MAXIMIZE_BOX)
        wx.Frame.__init__(self, parent, id, title, size=wx.Size(300,300), style = no_resize)
        panel = wx.Panel(self, -1, (50, 240))
        self.Bind(wx.EVT_CLOSE, self.onClose)
        img = wx.EmptyImage(75,100)
        self.imageCtrl = wx.StaticBitmap(panel, wx.ID_ANY, wx.BitmapFromImage(img), (110,85))
        self.play = wx.Button(panel, -1, 'Play/Pause', pos=(200,95))
        self.volup = wx.Button(panel, -1, 'Volume Up',  pos=(200,125))
        self.voldown = wx.Button(panel, -1, 'Volume Down', pos=(200,155))
        self.seekbut = wx.Button(panel, -1, 'Seek', pos=(200,185))
        clientlist=[]
        for client in Clients.keys ():
            clientlist.append(client)
        self.clientbox = wx.ListBox(panel, -1, (22,85), (75,130), clientlist)
        self.clienttext = wx.StaticText(panel, -1, 'Available Clients', (15,65))
##        self.sld = wx.Slider(panel, value=int(position), minValue=0, maxValue=int(duration), pos=(20, 200), size=(200, -1), style=wx.SL_HORIZONTAL)
##        self.sldval = wx.TextCtrl(panel, -1, duration, pos=(230, 200), size=(50,20))
##        self.sld.Bind(wx.EVT_SCROLL, self.OnSliderScroll)
        self.play.Bind(wx.EVT_BUTTON, self.pause)
        self.volup.Bind(wx.EVT_BUTTON, self.volUp)
        self.voldown.Bind(wx.EVT_BUTTON, self.volDown)
        self.seekbut.Bind(wx.EVT_BUTTON, self.seek)
        self.Bind(wx.EVT_LISTBOX, self.setClient)
        self.status=wx.StaticText(panel, -1, " ")
        self.duration=wx.StaticText(panel, -1, " ", pos=(0,20))
        self.position=wx.StaticText(panel, -1, " ", pos=(0,40))
        font = wx.Font(10, wx.DECORATIVE, wx.BOLD, wx.NORMAL)
        self.status.SetFont(font)
        self.duration.SetFont(font)
        self.position.SetFont(font)
        
    def onClose(self, event):
        self.Destroy()

    def scaleBitmap(self, bitmap, width, height):
        image = bitmap.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
        return image

##    def OnSliderScroll(self, e):
##        cli = self.clientbox.GetStringSelection()
##        self.cli = Clients[cli]
##        obj = e.GetEventObject()
##        val= obj.GetValue()
##        cmd = setPos+" "+str(val)
##        sendcmd(setPos(self.cli, cmd))
    
    def setClient(self, event):
        cli = self.clientbox.GetStringSelection()
        self.cli = Clients[cli]
        duration, position = self.statuscmd(self.cli)
        playing=str(self.sendcmd(self.cli, Clients[cli]['statuscmd']))
        if 'Cartoons' in playing:
            playing = playing.replace("/media/Cartoons/", "/media/External-4.0/Media/Lyndas/")  
        path= str(playing).split("/")[1:6]
        path = "/"+"/".join(path)
        try:
            imageFile = self.getImage(path)
        except: pass
        playing = playing.split("/")[-1].split(".")[0]
        gap = int(20 - len(playing)/2)
        self.status.SetLabel(" "*gap+"Now Playing: "+playing)
        self.duration.SetLabel("Length of movie: "+str(duration))
        self.position.SetLabel("Currently at: "+str(position))

    def getImage(self, path):
        for file in os.listdir(path):
            if file.endswith(".jpg"):
                imagepath = path+"/"+file
        img = wx.Image(imagepath, wx.BITMAP_TYPE_JPEG)
        image = self.scaleBitmap(img, 75, 100)
        self.imageCtrl.SetBitmap(wx.BitmapFromImage(image))
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
        
    def seek(self, event):
        self.sendcmd(self.cli, Seek+" 120")

    def statuscmd(self, cli, cmd=Status):
        print cmd 
        self.client=paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(cli['host'], port=cli['port'], username=cli['user'], password=cli['pass'])
        self.Stdin, self.Stdout, self.Stderr = self.client.exec_command(cmd)
        a = self.Stdout.read().strip()
        duration = a.split(':')[1].split("\n")[0]
        position = a.split(':')[2].split("\n")[0]
        duration, position = self.timecorrect(duration, position)
        duration = str(duration).split(".")[0]
        position = str(position).split(".")[0]
        self.client.close()
        return duration, position
    
    def sendcmd(self, cli, cmd):
        print cmd
        self.client=paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(cli['host'], port=cli['port'], username=cli['user'], password=cli['pass'])
        self.Stdin, self.Stdout, self.Stderr = self.client.exec_command(cmd)
        ret = self.Stdout.readlines()        
        return ret
    
    def update(self, cli, cmd):
        pass

if __name__ == '__main__':
    app = wx.App()
    frame = dbusControl(None, -1, 'DBUSGUI')
    frame.Show()
    app.MainLoop()
