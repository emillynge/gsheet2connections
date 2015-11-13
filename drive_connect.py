# -*- coding: utf-8 -*-
"""
Created on Wed Jan  7 21:59:58 2015

@author: emil
"""

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import csv
import locale
import codecs
from pprint import  pprint as pp
from operator import itemgetter
class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")
class CSVStringReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, string, dialect=csv.excel, encoding=None, **kwds):
        self.reader = csv.reader(string, dialect=dialect, **kwds)
        
    def next(self):
        row = self.reader.next()
        return [s for s in row]

    def __iter__(self):
        return self
        
def get_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    #gauth.SaveCredentials()
    drive = GoogleDrive(gauth)
    return drive
    
def get_csv(drive, id):
    file = drive.CreateFile({'id': id})
    file.FetchContent(mimetype='text/csv')
    string = file.GetContentString().encode('utf-8')
    reader = CSVStringReader(string.split('\n'))
    header = reader.next()
    M = [row for row in reader]
    return header, M
    
def get_memberships(drive, udvalgs_id):
    (header, M) = get_csv(drive, udvalgs_id)
    memberships = dict()
    categories = list()
    for row in M:
        cat = row[0]
        if cat:
            used=False            
            for pers in row[header.index(''):]:
                if pers:
                    used=True
                    pers = pers.lower()
                    if pers not in memberships:
                        memberships[pers] = list()
                    memberships[pers].append(cat)
            if used:
                categories.append(cat)
    return memberships, categories

def get_people(drive, personer_id):
    (header, M) = get_csv(drive, personer_id)
    people = dict()
    key_getter = itemgetter(header.index('Efternavn'), header.index('Fornavn'))
    for row in M:
        person = dict()
        for (i, h) in  enumerate(header):
            person[h] = row[i]
        people[', '.join(key_getter(row))] = person
    return people
            
            

        

