#!/usr/bin/python
# -*- coding:utf8 =*-
"""Generic object pickler and compressor

This module saves and reloads compressed representations of generic Python
objects to and from the disk.
"""

__author__ = "Bill McNeill <billmcn@speakeasy.net>"
__version__ = "1.0"

import pickle
import gzip

def zloads(filename):
  return load(filename)
def zdumps(obj, filename, mbin = pickle.HIGHEST_PROTOCOL):
  save(obj, filename, mbin)

def save(object, filename, bin = pickle.HIGHEST_PROTOCOL):
	"""Saves a compressed object to disk
	"""
	file = gzip.GzipFile(filename, 'wb')
	file.write(pickle.dumps(object, bin))
	file.close()


def load(filename):
	"""Loads a compressed object from disk
	"""
	file = gzip.GzipFile(filename, 'rb')
	buffer = ""
	while 1:
		data = file.read()
		if data == "":
			break
		buffer += data
	object = pickle.loads(buffer)
	file.close()
	return object


if __name__ == "__main__":
	import sys
	import os.path
	
	class Object:
		x = 7
		y = "This is an object."
	
	filename = sys.argv[1]
	if os.path.isfile(filename):
		o = load(filename)
		print "Loaded %s" % o
	else:
		o = Object()
		save(o, filename)
		print "Saved %s" % o
