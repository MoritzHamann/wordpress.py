import os
from wordpress import *
import sys


# global site object
sites = []

def register_wordpress(folder):
  w = Wordpress(folder)
  sites.append(w)


def find_all_wordpress(basefolder):
  # is basefolder a wordpress plugin
  if not os.path.exists(basefolder):
    return

  if Wordpress.is_wordpress_folder(basefolder):
    register_wordpress(basefolder)
  else:
    folders = list_folders(basefolder)
    for f in folders:
      absolute_path = os.path.join(basefolder, f)
      find_all_wordpress(absolute_path)



if len(sys.argv) < 2:
  print "please provide path name"
  exit()

find_all_wordpress(sys.argv[1])
