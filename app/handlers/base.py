#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import RequestHandler,asynchronous
from tornado.gen import engine,coroutine
from tornado import web
from tornado.escape import utf8
import string,os
from datetime import date
import logging
import bcrypt
from json import load,loads,dumps,dump
from lib.tokens import token_decode,gen_token

class BaseHandler(RequestHandler):
    """A class to collect common handler methods - all other handlers should
    inherit this one.
    """
    def prepare(self):
        #self.auth_check()
        self.input_data = dict()
        if self.request.method in ['POST','PUT'] and \
           self.request.headers["Content-Type"].startswith("application/json"):
            try:
                if self.request.body:
                    self.input_data = loads(self.request.body.decode("utf-8"))
                for k,v in self.request.arguments.items():
                    if str(k) != str(self.request.body.decode("utf-8")):
                        self.input_data[k] = v[0].decode("utf-8")
            except ValueError:
                self.dropError(400,'Fail to parse input data.')

    def get_current_user(self):
        max_days_valid=10
        # check for https comunication
        using_ssl = (self.request.headers.get('X-Scheme', 'http') == 'https')
        if not using_ssl:
            logging.info('Not using SSL')
        else:
            logging.info('Using SSL')
        # get the token for authentication
        token = self.request.headers.get("Linc-Api-AuthToken")
        res = None
        if token:
            # Decode to test
            try:
                token = token_decode(token,self.settings['token_secret'])
                # Check token and it will validate if it ir younger that 10 days
                vtoken = web.decode_signed_value(self.settings["cookie_secret"],'authtoken',token,max_age_days=max_days_valid)
            except:
                vtoken = None
            if vtoken:
                dtoken = loads(vtoken)
                # Check if the Tornado signed_value cookie functions
                if dtoken['username'] in self.settings['tokens'].keys() and \
                    self.settings['tokens'][dtoken['username']]['token'] == token:
                    res = dtoken
            else:
                # Validation error
                self.token_passed_but_invalid = True
        return res

    @asynchronous
    @engine
    def new_iid(self,collection,callback=None):
        iid = yield self.settings['db'].counters.find_and_modify(query={'_id':collection}, update={'$inc' : {'next':1}}, new=True, upsert=True)
        callback(int(iid['next']))

    def parseInput(self,objmodel):
        valid_fields = objmodel._fields.keys()
        newobj = dict()
        for k,v in self.input_data.items():
            if k in valid_fields:
                newobj[k] = v
        return newobj

    def switch_iid(self,obj):
        obj['id'] = obj['iid']
        del obj['iid']

    def setSuccess(self,code=200,message="",data=None):
        output_response = {'status':'success','message':message}
        if data:
            output_response['data'] = loads(self.json_encode(data))
        self.set_status(code)
        self.finish(output_response)

    def dropError(self,code=400,message=""):
        self.set_status(code)
        self.finish({'status':'error', 'message':message})

    def json_encode(self,value):
        return dumps(value,default=str).replace("</", "<\\/")

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

    def age(self,born):
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def encryptPassword(self,pattern):
        return bcrypt.hashpw(password, bcrypt.gensalt())

    def checkPassword(self,password,hashed):
        return bcrypt.hashpw(password, hashed) == hashed

    def imgurl(self,urlpath,imgtype='thumbnail'):
        # type can be: full,medium,thumbnail and icon
        url = self.settings['S3_URL'] + urlpath
        if imgtype == 'thumbnail':
            url = url + '_thumbnail.jpg'
        elif imgtype == 'full':
            url = url + '_full.jpg'
        elif imgtype == 'icon':
            url = url + '_icon.jpg'
        else:
        #imgtype == 'medium':
            url = url + '_medium.jpg'
        return url

    def sanitizestr(self,strs):
        txt = "%s%s" % (string.ascii_letters, string.digits)
        return ''.join(c for c in strs if c in txt)

class VersionHandler(BaseHandler):
    def get(self):
        self.setSuccess(200,self.settings['version']+' - animal defined: '+self.settings['animal'])

class DocHandler(BaseHandler):
    def get(self):
        self.set_header('Content-Type','text/html; charset=UTF-8')
        self.render('documentation.html')
