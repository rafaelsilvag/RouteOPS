#!/usr/bin/env python
#  coding=utf-8
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)
#  Modified by:
#         Rafael S. Guimarães <rafaelg@ifes.edu.br>
#
#  NERDS - Núcleo de Estudo em Redes Definidas por Software
#
import os
from lib.defs import *
from threading import RLock as lock
from pymongo import MongoClient

class Rib(object):
    """
        Rib - Routing Information Base
    """
    def __init__(self, ip):
        with lock():
            # Connect on MongoDB and access database
            self.db = MongoClient(MONGO_ADDRESS)[MONGO_DB_NAME]
            self.peer = self.db['peers'].find_one({'IP': ip})

    def __del__(self):
        try:
            self.client.close()
        except Exception, ex:
            pass

    def __setitem__(self, key, item):
        self.add(key,item)

    def __getitem__(self, key):
        return self.get(key)

    def add(self, key, item):
        with lock():
            if not self.peer['prefixes']:
                self.peer['prefixes'] = []
            if (isinstance(item, dict)):
                for p in self.peer['prefixes']:
                    if p['prefix'] == key:
                        self.peer['prefixes'].remove(p)
                        break
                item['prefix'] = key
                self.peer['prefixes'].append(item)
                self.db['peers'].save(self.peer)

    def get(self, key):
        with lock():
            for p in self.peer['prefixes']:
                if p['prefix'] == key:
                    return p
            return None

    def get_prefixes(self, key):
        with lock():
            result = []
            for p in self.peer['prefixes']:
                if p['prefix'] == key:
                    result.append(p)
            return result

    def get_all(self, key=None):
        with lock():
            if self.peer['prefixes']:
                return self.peer['prefixes']
            else:
                return None

    def filter(self, item, value):
        with lock():
            pass

    def update(self, item, value):
        with lock():
            if not self.peer['prefixes']:
                self.peer['prefixes'] = []
            for p in self.peer['prefixes']:
                if p['prefix'] == item:
                    self.peer['prefixes'].remove(p)
                    break
            value['prefix'] = item
            self.peer['prefixes'].append(value)
            self.db['peers'].save(self.peer)

    def update_neighbor(self, key, item):
        with lock():
            if (isinstance(item, dict)):
                for p in self.peer['prefixes']:
                    if p['prefix'] == key and p['next_hop'] == item['next_hop']:
                        self.peer['prefixes'].remove(p)
                        break
                item['prefix'] = key
                self.peer['prefixes'].append(item)
                self.db['peers'].save(self.peer)

    def delete(self, key):
        with lock():
            for p in self.peer['prefixes']:
                if p['prefix'] == key:
                    self.peer['prefixes'].remove(p)
                    self.db['peers'].save(self.peer)
                    break

    def delete_all(self):
        with lock():
            if not self.peer['prefixes']:
                self.peer['prefixes'] = []
            self.peer['prefixes'] = []
            self.db['peers'].save(self.peer)

    def delete_neighbor(self, key, neighbor):
        with lock():
            for p in self.peer['prefixes']:
                if p['prefix'] == key and p['next_hop'] == neighbor:
                    self.peer['prefix'].remove(p)
                    self.db['peers'].save(self.peer)
                    break
''' main '''
if __name__ == '__main__':
    # Update test
    myrib = Rib(ip='172.0.0.1')
    mainrib = Rib(ip='172.0.255.254')
    mainrib['110.0.0.0/24']  = {'next_hop':"172.0.0.2", 'as_path':'100 200 300' , 'med':'0'}
    myrib.update('110.0.0.0/24', {'next_hop':"172.0.0.2", 'as_path':'100 300' , 'med':'0'} )
    myrib['110.0.0.0/24']  = {'next_hop':"172.0.0.2", 'as_path':'100 200 300' , 'med':'0'}
    #myrib['120.0.0.0/24']  = {'next_hop':"172.0.0.2", 'as_path':'100 200 300' , 'med':'0'}
    mainrib.update_neighbor('110.0.0.0/24', {'next_hop':"172.0.0.1", 'as_path':'100 300' , 'med':'0'})
    #print myrib.get_all()
    print mainrib.get_all()
    myrib.delete_all()
    mainrib.delete_all()
    #val = myrib.filter('as_path', '300')
    #print val[0]['next_hop']
    peers = {
            'A': Rib('172.0.0.1'),
            'B': Rib('172.0.0.2'),
            'C': Rib('172.0.0.3'),
            'D': Rib('172.0.0.4'),
            'X': Rib('172.0.255.254')
    }
    for i in peers:
        peers[i].delete_all()
