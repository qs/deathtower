#!/usr/bin/env python
# coding:utf-8

import webapp2
import jinja2
import os
import re
import json
from cgi import escape
from google.appengine.api import users
from models import *


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class BaseHandler(webapp2.RequestHandler):
    def __init__(self, request, response):
        self.initialize(request, response)
        self.user = users.get_current_user()
        self.char = self.get_current_char() if self.user else None

    def get_current_char(self):
        # returns character object
        return None

    def render(self, tpl_file, tvals={}):
        tvals['logout'] = users.create_logout_url("/")
        tvals['char'] = self.char
        tpl = jinja_environment.get_template('templates/' + tpl_file + '.html')
        self.response.out.write(tpl.render(tvals))

    def render_json(self, data):
        self.response.out.write(json.dumps(data))


class WelcomeHandler(BaseHandler):
    def get(self):
            pass
            #self.render('welcome')


class WelcomeHandler(BaseHandler):
    def get(self):
            # promo page
            self.render('welcome')


class JoinHandler(BaseHandler):
    def get(self):
            # character creation screen
            self.render('join')

    def post(self):
            # create character
            self.redirect('/tour/')




app = webapp2.WSGIApplication([
    # auth
    ('/', WelcomeHandler),  # welcome promo-page avaliable without login
    ('/join/', JoinHandler), # if there is not character
    # tournmanet
    ('/tour/', TourHandler), # requests for tournaments
    ('/room/', RoomHandler), # location in tournament
    ('/final/', FinalHandler), # stats after finishing tounrament
    # character stats and items
    ('/char/', CharHandler), # stats editing
    ('/items/', ItemsHandler), # inventory

    ('/battle/', BattleHandler), # evething for battles
], debug=True)