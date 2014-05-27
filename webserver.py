#!/usr/bin/python2

import sys
import os
import subprocess
import traceback
import thread
import glob
import re
import random
import string
import urlparse
import json
import cgi
import Cookie
import BaseHTTPServer
import SocketServer
import time
import pronsole
import settings
import base64
import StringIO
import cv2
import logging

# our pronterface instance
printer=pronsole.pronsole()
#progress indicator state
progress="Idle 0 0"
# running processes (eg. Slic3r.pl)
processes=[]
# printer output buffer
recv_buffer=[]
# camera module
camera = cv2.VideoCapture(0)

# install printer output dissector
def recv_printer(line):
    global recv_buffer
    recv_buffer.append(line)
printer.recvlisteners.append(recv_printer)

# getting the image from the module
def get_image():
 retval, im = camera.read()
 return im

# server request handler
class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    # serve the printer's output
    # the output is kept at the recv_buffer and deleted after serving
    # thus the client only receives every message once.
    # TODO what if more then one client connects?
    def serve_printer(self):
        global recv_buffer
        self.send_response(200)
        self.end_headers()
        tmp_buffer=recv_buffer
        recv_buffer=[]
        for line in tmp_buffer:
            self.wfile.write(line)

    #capture the image
    def cam_capture(self,file_name):
        print("image capture name: "+file_name)
        for i in xrange(30):
            temp = get_image()
        print("Taking image...")
        camera_capture = get_image()
        cv2.imwrite("tmp_img/"+file_name, camera_capture)
         
    # serve a file from our folder
    def serve_file(self,url_path):
        print url_path
        if url_path=='/':
            url_path='/index.html'
        # map URL path to file in our directory
        file_path=os.path.abspath('./'+url_path)
        # prevent the client from accessing any file outside our directory
        server_path=os.path.abspath('.')
        if not file_path.startswith(server_path):
            raise Exception("Illegal path: "+path)
        # open the file to serve
        f = open(file_path)
        # send headers
        self.send_response(200)
        # establish correct mime type
        if "css" in url_path:
            self.send_header('Content-Type','text/css')
        elif ".js" in url_path:
            self.send_header('Content-Type','text/javascript')
        # establish a random session cookie 
        if not "Cookie" in self.headers or self.headers.get('Cookie').find('session=')==-1:
            self.send_header('Set-Cookie','session='+str(random.randint(0,0xFFFFFFFF)));
        self.end_headers()
        #send file content
        self.wfile.write(f.read())
        f.close()

    # serve a list of all configs in /configs folder
    def serve_configs(self):
        # send headers
        self.send_response(200)
        self.end_headers()
        #send file content
        for filename in glob.glob('configs/*.ini'):
            self.wfile.write(filename+"\n")

    # issue command via pronsole.py and return result       
    def serve_pronsole(self,cmds):
        self.send_response(200)
        self.end_headers()
        # issue command
        try:
            parts=cmds.split('\n')
            for cmd in parts:
	            printer.onecmd(cmd)
        except Exception as e:
            print e

    # run slicer and return gcode
    def serve_slic3r(self,session_id,config):
        global progress
        progress="Slicing... 1"
        self.send_response(200)
        self.end_headers()
        # invoke the slic3r with progress indicator
        logging.info('slicing start: '+ settings.slicer+' --debug --load '+config+' -o tmp/'+session_id+'.gcode tmp/'+session_id+'.stl')
        self.call_monitored(settings.slicer+' --debug --load '+config+' -o tmp/'+session_id+'.gcode tmp/'+session_id+'.stl',self.monitor_slic3r)
	# pass resulting .gcode file content to client
        gcode=open('tmp/'+session_id+'.gcode', 'r').read()
        self.wfile.write(gcode)
        progress="Slicing... 100"

    # cancel any ongoing operations: printing and slicing
    def serve_cancel(self, session_id):
        global progress 
        for process in processes:
                processes.remove(process)
                process.kill()
        if printer.p.printing:
                printer.onecmd('pause')
                printer.onecmd('M104 S0')
                printer.onecmd('M140 S0')
                printer.p.paused=False
                printer.p.printing=False
		
    
    # serve some state for UI feedback
    def serve_state(self,session_id):
        global progress
        global time
        self.send_response(200)
        self.end_headers()
        if printer.p.printing:
            progress="Printing... "+str(int(99*float(printer.p.queueindex)/len(printer.p.mainqueue))+1)+" "+str(int(time.time())-int(printer.p.starttime))+" "+str(int(printer.p.offset))
        state={
		'online':printer.p.online,        # if the printer is connected
		'printing': printer.p.printing,   # if the printer is currently printing
		'paused':printer.p.paused,        # if the printer is currently paused
		'clear':printer.p.clear,          # if the printer is clear to print
		'progress':progress               # progress of current slicing or printing operation
	}
        _json=json.dumps(state, indent=4)
        self.wfile.write(_json)

    # serve temp
    def serve_temp(self):
        global progress
        self.send_response(200)
        self.end_headers()
        if printer.p.online:
            _json=json.dumps(printer.onecmd('m105'), indent=4)
            self.wfile.write(_json)

    # serve position
    def serve_posi(self):
        global progress
        self.send_response(200)
        self.end_headers()
        if printer.p.online:
            _json=json.dumps(printer.onecmd('m114'), indent=4)
            self.wfile.write(_json)

        
    # parse a line of slic3r's stdout output and set progress indicator accordingly
    # currently only the 'filling layer' phase is tracked, that usually makes up most of the slicing time. 
    # TODO can we provide an estimation of progress at the earlier 'geometry' phase too?
    def monitor_slic3r(self,line):
        global progress
        # find number of layers to do. this is first mentioned as the last 'Making perimeters ...' output
        match=re.match('Making perimeters for layer ([0-9]+)',line)
        if match:
            self.slic3r_layers=int(match.group(1))
        # find actual 'Filling layer' message, indicating the most costly operations's progress
        # and set progress indicator
        match=re.match('Filling layer ([0-9]+)',line)
        if match:
            progress="Slicing... "+str(30+int(match.group(1))*70/self.slic3r_layers)
            print 'Slic3r progress:',progress

    # run a command and collect stderr, stdout to a buffer for interactive access
    # this is useful to serve a progress indicator for commands providing some progress output
    def call_monitored(self, cmdline, callback):
        global progress
        global processes
	
	# run the command
        process=subprocess.Popen(cmdline.split(' '),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        processes.append(process)
        # monitor command's outputs and invoke callback for each line
        while process.poll()==None:
                line=process.stdout.readline()
                if not line: break
                callback(line)
        if(process in processes):
                processes.remove(process)

    # save given data to file name
    def save_tmp(self,name,content):
       # copy content to file
       print 'Saving to ',name
       f=open(name,'w')
       f.write(content)
       f.close()

    # save uploaded data to /tmp folder
    # the files are named by the session_id and their field name as suffix.
    def save_uploads(self, session_id):
        contenttype_header=self.headers.getheader('content-type',False)
        if not contenttype_header:
             return
        # check if contenttype is multipart, exit otherwise
        ctype, pdict = cgi.parse_header(contenttype_header) 
        if not ctype == 'multipart/form-data': 
            return            
        parts=cgi.parse_multipart(self.rfile, pdict)
        # assert valid session_id
        if not session_id:
            raise Exception("No session cookie")
        # save every uploaded file, using the session_id as prefix and the HTML field name as suffix.
        for key, contents in parts.items():
            if key.startswith('configs/'):
                filename=key
            else:
                filename='tmp/'+session_id+'.'+key;
            self.save_tmp(filename, contents[0])

    # get session id from cookie
    def get_session(self):
        id=False
        if "Cookie" in self.headers:
            c = Cookie.SimpleCookie(self.headers["Cookie"])
            id=c['session'].value
            # make sure session is a number
            if not id.isdigit(): 
                raise Exception('Invalid session cookie')
        return id        

    # handle GET request by general serve_request()
    def do_GET(self):
        self.check_authentication()
        
    # handle POST request by general serve_request()
    def do_POST(self):
        self.check_authentication()

    # chek authentication user & password
    def check_authentication(self):
        global keyAuth
        if self.headers.getheader('Authorization') == None:
            self.do_AUTHHEAD()
            self.wfile.write('no auth header received')
            pass
        elif self.headers.getheader('Authorization') == 'Basic '+keyAuth:
            self.serve_request()
            pass
        else:
            self.do_AUTHHEAD()
            self.wfile.write('Please provide user & password')
            logging.warning('Authentication faild')
            pass

    #handle the authentication
    def do_AUTHHEAD(self):
        print "send header authenticated"
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"3dPrinter printrun server\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    # handle incoming request
    # 
    # provides several functions on the pathes: 
    # /pronsole, /configs, /printer, /slic3r, /state, /cancel, /upload.
    # see the corresponding serve_...() functions for details.
    #
    # for every other path, serve file from local directory. 
    # 
    def serve_request(self):
        try:
            # split URL parts (path, querystring)
            url_parts =urlparse.urlparse(self.path)
            # extract query string parameters:
            url_params=urlparse.parse_qs(url_parts.query) 
            # read session cookie 
            session_id=self.get_session()
            # save all POSTed files to /tmp
            self.save_uploads(session_id)
            
            if url_parts.path=='/pronsole':
                self.serve_pronsole(url_params.get('cmd')[0])
            elif url_parts.path=='/configs':
                self.serve_configs()
            elif url_parts.path=='/printer':
                self.serve_printer()      
            elif url_parts.path=='/slic3r':
                self.serve_slic3r(session_id,url_params.get('config')[0])
            elif url_parts.path=='/state':
                self.serve_state(session_id)
            elif url_parts.path=='/posi':
                self.serve_posi()
            elif url_parts.path=='/temp':
                self.serve_temp()
            elif url_parts.path=='/gcode':
                self.serve_file('tmp/'+session_id+'.gcode')
            elif url_parts.path=='/cancel':
                self.serve_cancel(session_id)
            elif url_parts.path=='/upload':
                self.send_response(200)
                self.end_headers()
                self.serve_cancel(session_id)
            elif ".jpg" in url_parts.path:
                self.send_response(200)
                url_path = url_parts.path
                file_path=os.path.abspath('./'+url_path)
                self.cam_capture(url_path[9:])
                logging.info('Pic taken')
                self.send_header('Content-Type','image/JPEG')
                f = open(file_path,'rb')
                self.end_headers()
                #send file content
                self.wfile.write(f.read())
                logging.info('Pic save & send')
                #del(camera) 
            else:
                self.serve_file(url_parts.path)
        except Exception as e:
            print traceback.format_exc()
            logging.exception("exception: ")
            self.send_error(404,'Request to "%s" failed: %s' % (self.path, str(e)) )

# multithreading server
class ThreadingServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    global keyAuth 
    if len(sys.argv)<2:
        print "usage webserver.py [username:password]"
        sys.exit()
    keyAuth = base64.b64encode(sys.argv[1])
    pass

try:
    # make sure the current working dir is the one of this script (we serve files from it!)
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0]))) 
    # create server 
    server = ThreadingServer(('', settings.port), RequestHandler) # multi threaded server
    #server = BaseHTTPServer.HTTPServer(('', settings.port), RequestHandler)  # single threaded server
    print 'Server running on port '+str(settings.port)
    logging.basicConfig(filename='log.txt', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')
    # and run it...
    server.serve_forever()
except KeyboardInterrupt:
    # on ctrl+c try to close cleanly
    # TODO this doesn't always seem to work, especially if stdout from pronsole is redirected it seems
    logging.exception("KeyboardInterrupt exception: ")
    server.socket.close()

