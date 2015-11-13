# -*- coding: utf-8 -*-
"""
Created on Thu Jan  8 09:32:02 2015

@author: emil
"""
from pprint import pprint as pp
import re
from manage import ConnectionsManager
import sys
from datetime import datetime
import os
from drive_connect import get_memberships, get_drive, get_csv, get_people
DOMAIN='http://team.puf-lyx.dk/'
udvalg_id = '1cXxERjpa7qKlo00vbXtXfrTypT290BcXuwHvLWOj4jE'
personer_id = '1osFV507OVl8AxTAafgeiuHnuW0lBbAnPTGxrCjeevMQ'
LEVEL2int = {'Aktiv': 1, 'Passiv': 2, 'Tidligere': 3}
LEVEL2cat = {'Aktiv': ['Team Lyx'], 'Passiv': ['Team Lyx', 'Passiv'], 'Tidligere':['Tidligere']}
LEVELcats = list()
FNULL = open(os.devnull, 'w')
STDOUT = open('/dev/stdout', 'w')

for cats in LEVEL2cat.values():
    LEVELcats += cats




def update_all(cm, m, cats, people, level=3, logfile=STDOUT):
    logfile.write("performing update at %s" % datetime.now().isoformat() + '\n')
    check_membership_slugs(people, m, logfile=logfile)
    for nk in cm.profile_names:
        if nk in people and LEVEL2int[people[nk]['niveau']] <= level:
            p = cm.get_profile(nk)
            update_mails(p, people, logfile=logfile)
            update_cats(p, m, cats, people, logfile=logfile)
            cm.update_profile(p, dryrun=False, force=True)
        
def check_membership_slugs(people, memberships, logfile=STDOUT):
    slugs = [person['pufslug'] for person in people.values()]
    for (slug, cat) in  memberships.iteritems():
        if slug not in slugs:
            logfile.write("member '%s' in category %s matches no slugs\n" %  (slug, cat))
    
        
def update_mails(profile, people, logfile=STDOUT):
    nk = profile.name_key()
    if nk in people:
        person = people[nk]
        mails = [m for key, m in person.iteritems() if re.findall('mail', key) and m]
        profile.fields['email'].set_mails(mails)
        profile.fields['email'].set_preferred(person['pufmail'])
    else:
        logfile.write("profile %s not found in people\n" % nk)
        
def update_cats(profile, memberships, categories, people, logfile=STDOUT):
    nk = profile.name_key()
    categories = list(categories)
    categories += LEVELcats
    if nk in people:
        person = people[nk]
        if person['pufslug'] in memberships:
            membership = memberships[person['pufslug']] + LEVEL2cat[person['niveau']]
        else:
            membership = LEVEL2cat[person['niveau']]
        for cat in membership:
            profile.fields['cat'].add_category(cat)
        for cat in [_cat for _cat in categories if _cat not in membership]:
            profile.fields['cat'].remove_category(cat)
    else:
        logfile.write("profile %s not found in people\n" % nk)

if __name__ == '__main__':
    drive = get_drive()
    (m, cats) = get_memberships(drive, udvalg_id)
    people = get_people(drive, personer_id)
    kwargs_updater = dict()
    kwargs_updater['level'] = 1
    kwargs_cm = dict()
    if len(sys.argv) > 1:
        argv = sys.argv[1:]
        for (key, value) in zip(argv[::2],argv[1::2]):
            if key in ['-l', '--logging']:
                if value.lower() == 'none':
                    logfile =  FNULL
                elif value.lower() == 'print':
                    logfile =  STDOUT
                else:
                    logfile = open(value, 'a')
                kwargs_updater['logfile'] = logfile
                kwargs_cm['logfile'] = logfile
            else:
                print "Invalid input argument '%s'" % key
    cm = ConnectionsManager(DOMAIN, **kwargs_cm)
    update_all(cm, m, cats, people, **kwargs_updater)
    logfile.close()
    
#p = cm.get_profile('Breum, Gyda')
