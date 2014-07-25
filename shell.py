#!/usr/bin/env python

import cmd
import glob, os, time
import sys, subprocess 
import math
import gettext




class shell(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        
    def do_shell(self,l):
        exec(l)
    





if __name__=="__main__":
    
	print    sys.argv[1:]
    
