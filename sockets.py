#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, redirect, url_for
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        print "at add_set_listener"
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()

# code taken and modified from
# https://github.com/abramhindle/WebSocketsExamples
class Client:
    def __init__(self):
        self.queue = queue.Queue()
    
    def put(self, v):
        self.queue.put_nowait(v)
    
    def get(self):
        return self.queue.get()


clients = list()

def set_listener( entity, data ):
    return

myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return redirect(url_for('static', filename='index.html'))

# code taken and modified from
# https://github.com/abramhindle/WebSocketsExamples
def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    try:
        while True:
            msg = ws.receive()
            if (msg is not None):
                packet = json.loads(msg)
                for client in clients:
                    client.put( packet )
            else:
                break
    except Exception as e:
        clients.remove(client)
        gevent.kill(g)

# code taken and modified from
# https://github.com/abramhindle/WebSocketsExamples
@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    client = Client()
    clients.append(client)
    g = gevent.spawn( read_ws, ws, client )
    try:
        while True:
            msg = client.get()
            if "new" in msg:
                ws.send(json.dumps(myWorld.world()))
            else:
                for key in msg:
                    if "data" in key:
                        data = msg[key]
                    else:
                        entity = msg[key]
                        myWorld.set(entity, data)
                        ws.send(json.dumps(data))

    except Exception as e:# WebSocketError as e:
        print "WS Error %s" % e
    finally:
        clients.remove(client)
        gevent.kill(g)

def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    entityvalue = flask_post_json()
    myWorld.set(entity, entityvalue)
    return json.dumps(entityvalue)

@app.route("/world", methods=['POST','GET'])
def world():
    entities = {}
    current_world = myWorld.world()
    return json.dumps(current_world)

@app.route("/entity/<entity>")
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    data = myWorld.get(entity)
    return json.dumps(data)

@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    current_world = myWorld.clear()
    return json.dumps(current_world)




if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
#app.run()
    os.system("bash run.sh");
