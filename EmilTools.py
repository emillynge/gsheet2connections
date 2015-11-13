# -*- coding: utf-8 -*-
"""
Created on Wed Jan  7 11:20:22 2015

@author: emil
"""

import os
from subprocess import Popen

FNULL =  open(os.devnull, "w")
def view_html(html, i=0):
    fp = open('/tmp/out-%s.html' % i, 'w')
    fp.write(html)
    fp.close()
    Popen(['chromium-browser', '/tmp/out-%s.html' % i], stderr=FNULL, stdout=FNULL)
    return 0

def update_html(html, i=0):
    fp = open('/tmp/out-%s.html' % i, 'w')
    fp.write(html)
    fp.close()
    return 0
    
class RegexDict(dict):
    def rget(self, reg_exp):
        import re
        results = list()
        reg_exp_comp = re.compile(reg_exp)
        for (key, value) in self.iteritems():
            if reg_exp_comp.findall(key):
                results.append((key, value))
        return ResultList(results)
        
    def __getitem__(self, key):
        if key[0] == '\r':
            return self.rget(key[1:])
        return super(RegexDict, self).__getitem__(key)

class ResultList(list):
    def rget(self, reg_exp, obj):
        import re
        if isinstance(obj, (list, ResultList) ):
            obj = list(obj)
            for (i, el) in enumerate(obj):
                obj[i] = self.rget(reg_exp, el)
            return obj
            
        if isinstance(obj, tuple):
            return (obj[0], self.rget(reg_exp, obj[1]))
            
        if isinstance(obj, RegexDict):
            return obj.rget(reg_exp)
        
        if isinstance(obj, dict):
            return RegexDict(obj).rget(reg_exp)
            
        if isinstance(obj, (str, unicode)):
            return re.findall(reg_exp, obj)
        return obj

    def __getitem__(self, key):
        if isinstance(key, str) and key[0] == '\r':
            return ResultList(self.rget(key[1:], self))
        return super(ResultList, self).__getitem__(key)
    
    def cut(self, levels, this_level=0, obj=hash('ROOT')):
        if obj == hash('ROOT'):
            obj = self
        if this_level == levels:
            return [obj]
        next_level = this_level + 1
#        if this_level == 0:
#            result = ResultList()            
#            for el in obj:
#                result.append(self.cut, levels, this_level=next_level, obj=el)
#       
        if isinstance(obj, list) and (not obj or not isinstance(obj[0], tuple)):
            return obj
            
        if this_level == 0 or isinstance(obj, list):
            result = list()
            for el in obj:
                result += self.cut(levels, this_level=next_level, obj=el)
            return result
        
        if isinstance(obj, tuple) and len(obj) == 2:
            if levels == -1 and not isinstance(obj[1], list):
                return [obj[1]]
            return self.cut(levels, this_level=next_level, obj=obj[1])
        
        return [obj]
                
        
        
                
            
        
        