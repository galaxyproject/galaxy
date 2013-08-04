#! /usr/local/bin/python2.4
# generic local file library for plink
# returns a file list from a
# designated library
import os,glob

def getFlist(path='/usr/local/data/pedfiles',wildcard='*.ped'):
   """
   for now just a folder glob - might become a database lookup or anything else!
   """
   plist = glob.glob(wildcard)
   return plist






