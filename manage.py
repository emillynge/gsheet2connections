# -*- coding: utf-8 -*-
"""
Created on Wed Jan  7 12:07:21 2015

@author: emil
"""

import requests
from EmilTools import view_html, update_html
import re
from operator import itemgetter
from pprint import pprint as pp
from random import random
from datetime import datetime
import json
with open('connectionslogin.json') as fp:
    CONNECTIONSPASS = json.load(fp)

from requests_toolbelt import MultipartEncoder
try:
    from scrapy.selector import Selector
except ImportError:
    from scrapy.selector import HtmlXPathSelector
    class Selector(HtmlXPathSelector):
        def xpath(self,xpath):
            return self.select(xpath)

STDOUT = open('/dev/stdout', 'w')
DEFLOG = lambda message: STDOUT.write(message + '\n')
class ConnectionsManager(object):
    def __init__(self, domain, logfile=STDOUT):
        self.link2id = lambda link: int(re.findall('id=(\d+)', link)[0])
        #self.path_url = lambda link: BASE_URL + re.findall('(.+)\?', link)[0]
        self.regexp = {'cb': re.compile('<input[^>]+type="checkbox"[^>]*name="([^"]+)"[^>]*value="([^"]+)"[^>]*CHECKED[^>]*>'),
                       'rad': re.compile('<input[^>]+type="radio"[^>]*name="([^"]+)"[^>]*value="([^"]+)"[^>]*\\\'checked\\\'[^>]*>'),
                       'hid': re.compile('<input[^>]+type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]+)"[^>]*>'),
                       'tex': re.compile('<input[^>]+type="text"[^>]*name="([^"]+)"[^>]*value="([^"]+)"[^>]*>'),
                       'amp': re.compile('&amp;'),
                       'profile_links': re.compile('"Edit ([^"]+)" href="([^"]+cn-action=edit[^"]+)"'),
                       'cat': re.compile('"check-category-(\d+)[^>]+>([^<]+)'),
                       'texa': re.compile('<textarea[^>]+id="([^-"]+)"[^>]*>(.*?)</textarea>')}
        self.login_link = domain + 'wp-login.php'
        self.admin_path = domain + 'wp-admin/'
        self.rm_amp = lambda link: self.regexp['amp'].sub('&', link)
        self.s = requests.Session()
        self.s.post(self.login_link, data=CONNECTIONSPASS)
        self.logfile = logfile
        res_manage = self.get_admin("admin.php?page=connections_manage")
        self.profile_links = dict(self.regexp['profile_links'].findall(res_manage.content))
        self.cat2id = dict()
        self.id2slug = dict()
        self.slug2cat = dict()
        res_cat = self.get_admin('admin.php?page=connections_categories')
        sel = Selector(text=res_cat.text)
        rows = sel.select('//tbody[@id="the-list"]/tr')
        
        for row in rows:
            id = row.select('@id').extract()[0].split('-')[1]
            cat = re.sub(u'\u2014 ','', row.select('td/a/text()').extract()[0])
            slug = row.select('td[@class="slug column-slug"]/text()').extract()[0]
            self.cat2id[cat] = id
            self.id2slug[id] = slug
            self.slug2cat[slug] = cat
    def log(self, message):
        self.logfile.write(message + '\n')
    def get_admin(self, link, **kwargs):
        return self.s.get(self.admin_path + self.rm_amp(link), **kwargs)
    
    def post_admin(self, link, **kwargs):
        return self.s.post(self.admin_path + self.rm_amp(link), **kwargs)
    
    @property
    def profile_names(self):
        return self.profile_links.keys()
        
    def get_profile(self, name):
        res =self.get_admin(self.profile_links[name])
        form = re.findall('<form id="cn-form".+?</form>',re.sub('[\r\n]','',res.content))[0]
        submit_link = re.findall('<form[^>]+action="([^"]+)"[^>]+>',form)[0]
        fields = self.regexp['rad'].findall(form) + \
                        self.regexp['hid'].findall(form) + \
                        self.regexp['cb'].findall(form) + \
                        self.regexp['tex'].findall(form) + \
                        self.regexp['texa'].findall(form) + [('update', 'Opdater')]
            
        return Profile(submit_link, fields, self.cat2id, self.id2slug, logger=self.log)
    
    def get_categories(self):
        res =self.get_admin(self.profile_links.values()[0])
        form = re.findall('<form id="cn-form".+?</form>',re.sub('[\r\n]','',res.content))[0]
        cat2id = dict([(it[1], it[0]) for it in self.regexp['cat'].findall(form)])
        return cat2id
    
    def update_profile(self, profile, force=False, dryrun=False):
        if profile.change or force:
            self.log("Updating %s..." % profile.name_key())
            if not dryrun:
                m = MultipartEncoder(fields=profile.dump())
                self.post_admin(profile.submit_link, data=m,
                          headers={'Content-Type': m.content_type})
            self.log('done')
        else:
           self.log("No change, not updating %s" % profile.name_key())

class Profile(object):
    def __init__(self, submit_link, fields, cat2id, id2slug,
     logger=DEFLOG):
        self.log = logger
        self.submit_link = submit_link
        self.cat2id = cat2id
        self.id2slug = id2slug
        self.change = False
        self.fields = {'x'*20: RejectField(self),'_aux': Field(self),
                       'cat': CategoryField(self), 'email': EmailField(self),
                        'name': NameField(self)}
        f_list = sorted(self.fields.items(), key=itemgetter(0), reverse=True)
        for (name, value) in fields:
            for (f_t, f) in f_list:
                if f.match(name, value):
                    f.insert(name, value)
                    break
    def dump(self, field=None):
        if field:
            return self.fields[field].dump()
        fields = list()
        for f in self.fields.values():
            fields += f.dump()
        return fields
    
    def name_key(self):
        return self.fields['name'].name_key()


                
class Field(object):
    def __init__(self, parent):
        self.log = parent.log
        self._parent = parent
        self.data = dict()
        self.split_rexp = None 
        self.splitter = None
        self.set_splitter('[\]\[]')
        self.left_pad = '['
        self.right_pad = ']'
    
    def set_splitter(self, regexp):
        self.split_rexp = re.compile(regexp)
        self.splitter = lambda string: [t for t in self.split_rexp.split(string) if t]
        
    def insert(self, name, val):
        keys = self.splitter(name)
        lastkey = keys[-1]
        keys = keys[:-1]
        node = self.data
        for key in keys:
            if key not in node:
                node.update({key: dict()})
            node = node[key]
        node[lastkey] = val
        
    def match(self, name, value):
        return True
    
    def dump(self):
        return self._iter_dump(self.data, first=True)
        
    def _iter_dump(self, node, first=False):
        if isinstance(node, dict):
            strings = list()
            for (key, val) in node.iteritems():
                for (string, leaf) in self._iter_dump(val):
                    if first:
                        strings.append((key + string, leaf))
                    else:
                        strings.append((self.left_pad + key + self.right_pad + string, leaf))
            return strings
        else:
            return [('', node)]

class NameField(Field):
    def __init__(self, parent):
        super(NameField, self).__init__(parent)
        self.set_splitter('_')
        self.left_pad = '_'
        self.right_pad = ''
    
    def match(self, name, val):
        return self.splitter(name)[-1] in ['name', 'suffix']
    
    def name_key(self):
        if 'last' in self.data and 'first' in self.data:
            return ', '.join([self.data['last']['name'], 
                              self.data['first']['name']])
        else:
            return None

class RejectField(Field):
    def insert(self, name, val):
        pass
    
    def match(self, name, val):
        if re.findall('::FIELD::', name):
            return True
        return False     
    
    def dump(self):        
        return []

class EmailField(Field):
    def __init__(self, parent):
        super(EmailField, self).__init__(parent)
        (self.mail_type2serials, self.serial2mail_type) = self.parse_adresses()
                              
    def insert(self, name, val):
        super(EmailField, self).insert(name, val)
        serial = self.splitter(name)[1]
        mail_type = self.parse_address(serial)
        if mail_type:
            self.serial2mail_type[serial] = mail_type
            self.mail_type2serials[mail_type].append(serial)
            self.set_type(serial, mail_type)
                
        
    def match(self, name, val):
        return self.splitter(name)[0] == 'email'
    
    def change_address(self, serial, address, mail_type):
        if self.data['email'][serial]['address'] != address:
            if mail_type != self.serial2mail_type[serial]:
                self.mail_type2serials[mail_type].remove(serial)
                self.serial2mail_type[serial] = mail_type
            self.data['email'][serial]['address'] = address
            self.set_type(serial, mail_type)
            self._parent.change = True
    
    def set_type(self, serial, mail_type):
        if mail_type == 'private':
            self.data['email'][serial]['type'] = 'private'
        else:
            self.data['email'][serial]['type'] = 'work'
    
    def new_address(self, address):
        serial = int(random()*10**13)
        self.insert('email[%d][address]' % serial, address)
        mail_type = self.serial2mail_type[str(serial)]
        if mail_type == 'private':
            self.insert('email[%d][visibility]' % serial, 'private')
        else:
            self.insert('email[%d][visibility]' % serial, 'public')
        self._parent.change = True
        
    def address2serial(self, address):
        serials = [s for s in self.data['email'].keys() if s != 'preferred']
        for serial in serials:
            if self.data['email'][serial]['address'] == address:
                return serial
        return None
            
    def set_preferred(self, address):
        s = self.address2serial(address)
        if 'preferred' not in self.data['email'] or self.data['email']['preferred'] != s:
            self.data['email']['preferred'] = s
            self._parent.change = True
        
    def set_mails(self, addresses):
        serials = list(self.serial2mail_type.keys())
        addresses = list(addresses)
        scrap_serials = list()
        
        while serials: # Identify the unchanged adresses
            serial = serials.pop()
            _address = self.data['email'][serial]['address'] 
            if _address not in  addresses:
                scrap_serials.append(serial)    # this mail has changed
            else:
                addresses.remove(_address)      # this mail is unchanged
        
        while addresses: # Assign unseen adresses to unused serials
            address = addresses.pop()
            mail_type = self.parse_address(None, address=address)
            if scrap_serials:
                serial = scrap_serials.pop()
                self.change_address(serial, address, mail_type)
            else:
                self.log("%s has no spare %s adresses. Making new" % (self._parent.name_key(),mail_type))
                self.new_address(address)
                
        for serial in scrap_serials:
            del(self.data['email'][serial])
            
    def parse_address(self, serial, address=None):
        if not address:
            if serial == 'preferred':
                return None
            mail_data = self.data['email'][serial]
            if 'address' not in mail_data:
                return None
            address = mail_data['address']
            
        if address.split('@')[-1] == 'puf-lyx.dk':
            if address.split('@')[0] in self._parent.id2slug.values():
                return 'cat_slug'
            else:
                return 'pers_slug'
        else:
            return 'private'
        
    def parse_adresses(self):
        mail_type2serials = {'cat_slug': list(),
                             'pers_slug': list(),
                             'private': list()}
        serial2mail_type = dict()
        if 'email' in self.data:
            for serial in self.data['email'].keys():
                mail_type = self.parse_address(serial)
                if mail_type:
                    mail_type2serials[mail_type].append(self.data['email'][serial]['address'])
                    serial2mail_type[serial] = mail_type
        return mail_type2serials, serial2mail_type
            
        
class CategoryField(Field):
    
    def clear_all(self):
        self.data = dict()
    def add_category(self, category):
        self.set_category(category, True)
    
    def remove_category(self, category):
        self.set_category(category, False)
        
    def set_category(self, category, state):
        category = category.decode('utf8')
        if category not in self._parent.cat2id:
            self.log('WARNING %s is not a valid category' % category)
        else:
            id = self._parent.cat2id[category]
            if id in self.data:
                if self.data[id] != state:
                    self._parent.change = True
                    self.log('%s %s for %s' % ('adding' if state else 'removing',
                                            category.encode('utf8'), self._parent.name_key()))
                    self.data[id] = state
            else:
                self.data.update({id: state})
                if state == True:
                    self._parent.change = True
                    self.log('%s %s for %s' % ('adding' if state else 'removing',
                                            category.encode('utf8'), self._parent.name_key()))
                
    def insert(self, name, val):
        self.data[val] = True
    
    def match(self, name, val):
        return name == 'entry_category[]'         
    
    def dump(self):        
        return [('entry_category[]', key) for (key, val) in  self.data.iteritems() if val]
    
#fp.close()
    

"""        
m = MultipartEncoder(fields=dict(fields))
res4 = requests.post(link, data=m,
                  headers={'Content-Type': m.content_type})
re.findall('"check-category-(\d+)[^>]+>([^<]+)',form)["""
