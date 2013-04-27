#VisPrinter

This is a highly modified fork of dronus' web front end for Printrun. Most of the framework was undertaken by dronus, with development here focussing on adding functionality and a GUI that works on a 800x480px touch screen.

#Alterations/Changes/Improvements

-Removal of slicing interface/stl rendering

-Addition of three tabs for controls, 3D g-code preview and console.

-Realtime temperature and position feedback to similate that seen on LCD screens like Panelolu, Makerbot, etc.

-Manual connect, disconnect and reset for greater control.

-Removed bugs with print/pause/resume/cancel buttons so they show/hide at the correct times.

-Added browser controls to assist with keyboardless touch devices.

-Added touch friendly controls for extruder/bed temp, extrusion/retraction, homing and manual printer movements.

-Cleaned up console output to remove unimportant informaton.

-Added clear button for console.

-Modified webGL g-code preview for better 'camera' positioning and faster rendering. This is still limited to 64K vertices so large files will not render past a certain point.

-Added popup option to render or cancel 3D g-code render, improvingperformance on low power devices.

-Added automatic retrieval of last g-code sent to webserver on page refresh.

-Refined print progress bar to include numeric percentage, time elapsed and estimated time remaining. This persists even with a page refresh.

-Added heater kill on print cancel.

-Added linux bash script to start python server and open chromium to correct page.

#Intended Usage

The specific application in mind was the control of a Solidoodle 2 printer wit a Pengpod700. The pengpod runs the Printrun webserver and has a samba share where g-code can be dropped from other computers on the network. The prints can then be started/monitored on the Pengpod. Other computers on the network can still connect and control the printer.

#Requirements

-Modern browser capable of HTML5 and webGL.

-Device with python installed and capable of connecting to a reprap style printer via USB.

#Credits

-Based on Printrun - https://github.com/kliment/Printrun

-Uses lightgl.js - https://github.com/evanw/lightgl.js

-Forked from VisPrinter - https://github.com/dronus/VisPrinter

-Inspired by fsantini's pengpod printrun - https://github.com/fsantini/Printrun-pengpod700

-Further help from fsantini in setting up the pengpod and samba share.

#Installation and startup (short)

1. Unzip files into a location of your choice.

2. Run webserver.py

3. Direct a browser window to http://127.0.0.1:8082/index.html on that device, or http://<ip address of device>:8082/index.html from a different device.

#Installation and setup (specific and detailed for Pengpod 700)

Step 1. Install python.

Open a terminal window and enter:

```sudo apt-get install python-serial python-wxgtk2.8 python-pyglet```

This will install python automatically.

Step 2. Install samba.

In a terminal window, enter:

```sudo apt-get install samba```

This will install samba automatically.

Step 3. Setup a samba share for g-code (with thanks to fsantini).

In a terminal window, enter:

```
mkdir /home/linaro/gcode
chmod a+rwx /home/linaro/gcode
```

This creates the directory and makes it readable and writable to all.

Now the folder must be setup. Open up the configuration file with:

```sudo nano /etc/samba/smb.conf```

If you want a nicer GUI text editor, apt-get install gedit and then open the file as follows:
`sudo gedit /etc/samba/smb.conf

The following should be placed at the end:

```
[gcode]
    path = /home/linaro/gcode
    guest ok = yes
    browseable = yes
    read only = no
```

Save and close the file.

Now restart samba in the terminal by entering:

```sudo service smbd restart```

On a windows machine, under network, 'LINARO-ALIP' or similar should appear with the gcode folder inside it.
STL files can be sliced and processed by a more powerful computer, and then the g-code moved into this folder to be opened and printed from the pengpod

Step 4. Install this repo.

Using teminal, make a folder to store the contents of this repo:

```
sudo mkdir /home/linaro/visp
chmod a+rwx /home/linaro/visp
```

Now unzip this repo into that folder.
If you want a nice GUI zip tool, apt-get install p7zip-full and then file-roller.
You will need to make some of the files writable/executable in the terminal:

```
sudo chmod a+rwx /home/linaro/visp/tmp
sudo chmod a+rwx /home/linaro/visp/webserver.py
sudo chmod a+rwx /home/linaro/visp/visp.sh
```

Step 5. Make desktop shortcut.

Create a new shortcut on the desktop, entering VisPrinter (or whatever you like) in the first popup.
In the second popup screen, set the name as the same as previous.
Under command, enter:

```bash /home/linaro/visp/visp.sh```

Click ok.

Step 6. Run the shell script.

Click of you new shortcut to run the shell script. Select 'execute' if a popup appears the first time.
The script will start the printer server webserver.py in a terminal window and then open chromium browser to 127.0.0.1:8082/index.html
If the terminal window is closed, the printer server will close also.
If you wish to run the webserver in the background, manually execute webserver.py by itself.
Once the webserver is running, other computers may access it through the browser. I set up the ip address of the penpod to always be the same with my router.
In my case, I can connect from my home network at http://192.168.1.11:8082/index.html where 192.168.1.11 is the ip address of the pengpod.
