#!/usr/bin/env python
# coding:utf-8

import webapp2
import jinja2
import os
import json
from cgi import escape
from google.appengine.api import users
from models import *
import re
import time
import datetime
import google.appengine.ext.db
from google.appengine.ext import db
from google.appengine.api import memcache
from util import *
from util_db import *
from google.appengine.api import users

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

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class MainHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            msg = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" %
                   (user.nickname(), users.create_logout_url("/")))
        else:
            msg = ("<form action=\"%s\">"
                   "<input type=\"submit\" value=\"Login to Google\">"
                   "</form>" %
                   users.create_login_url("/"))
        self.response.out.write("<html><body>%s</body></html>" % msg)

class WelcomeHandler(BaseHandler):
    def get(self):
            # promo page
            if self.request.cookies.get("username_id"):
                   self.write("""
                   Welcome back!  <button onClick="location.href='/logout'">logout</button>
                   """)
            else:
                   self.render('welcome')

class Signup(BaseHandler):
    def get(self):
        if self.request.cookies.get("username_id"):
               self.redirect('/')
        self.render('signup')
    
    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')
        params = dict(username = username, email = email)
        error_code = False
        accounts = [u.username for u in list(db.GqlQuery("SELECT username FROM Users"))]
        
        if not valid_username(username):
            params['username_error'] = "That's not a valid username."
            error_code = True
        else:
            if username in accounts:
                    params['username_error'] = "Username is taken."
                    error_code = True
        if not valid_password(password):
            params['password_error'] = "That's not a valid password."
            error_code = True
        if not password==verify:
            params['verify_error'] = "Password didn't match"
            error_code = True
        if not valid_email(email):
            params['email_error'] = "That's not a valid e-mail"
            error_code = True
        
        if error_code:
            self.render('signup', params)
        else:
            account = Users(username = username, password = make_secure_pw(password), email = email)
            account.put()
            account_id = account.key().id()
            cookie_val = make_secure_val(str(account_id))
            self.response.headers.add_header("Set-Cookie", "username_id=%s; Path=/" % str(cookie_val))
            self.redirect('/')

class Login(BaseHandler):
    def get(self):
        self.render('login')
        
    def post(self):
        username = self.request.get('username')
        pw = self.request.get('password')
        url = self.request.get('url')
        
        account = db.GqlQuery("SELECT * FROM Users WHERE username = :1", username).get()
        
        if not account:
            self.render('login', {'error': 'Invalid pair'})
        else:
            pw_hash = account.password
            if check_secure_pw(pw, pw_hash):
                account_id = account.key().id()
                cookie_val = make_secure_val(str(account_id))
                self.response.headers.add_header("Set-Cookie", "username_id=%s; Path=/" % str(cookie_val))
                self.redirect('/')
            else:
                self.render('login', {'error': 'Invalid pair'})
        
class Logout(BaseHandler):
    def get(self):
        self.response.headers["Set-Cookie"] = "username_id=; Path=/"
        self.redirect('/')


class JoinHandler(BaseHandler):
    def get(self):
            # character creation screen
            self.render('join')

    def post(self):
            # create character
            self.redirect('/tour/')


class TourHandler(BaseHandler):
    def get(self):
            # list ofr tounaments
            self.render('tour')

    def post(self):
            # join or create tournament request
            self.redirect('/tour/')


class RoomHandler(BaseHandler):
    def get(self):
            # room screen
            self.render('room')

    def post(self):
            # move to another room, attack person or pickiu item
            self.redirect('/room/')


class FinalHandler(BaseHandler):
    def get(self):
            # show stats after final battle finishing tournament
            self.render('final')


class CharHandler(BaseHandler):
    def get(self):
            # character screen, stats
            self.render('char')

    def post(self):
            # update stats
            self.redirect('/char/')


class ItemsHandler(BaseHandler):
    def get(self):
            # inventory screen
            self.render('items')

    def post(self):
            # use item, put on, take off item, drop down
            self.redirect('/items/')


class BattleHandler(BaseHandler):
    def get(self):
            # compose your turn, wait for others
            self.render('battle')

    def post(self):
            # char if everyone compose turn compute turns
            self.redirect('/battle/')


class GardenHandler(BaseHandler):
    def get(self):
            # plants, friuts
            self.render('garden')

    def post(self):
            # watering plants, puck up fruits, remove plant
            self.redirect('/garden/')



app = webapp2.WSGIApplication([
    # auth
    ('/', WelcomeHandler),  # welcome promo-page avaliable without login
    ('/login\/?', Login), #login
    ('/logout', Logout), #signup
    ('/signup\/?', Signup),
    ('/join/', JoinHandler), # if there is not character
    # tournmanet
    ('/tour/', TourHandler), # requests for tournaments
    ('/room/', RoomHandler), # location in tournament
    ('/final/', FinalHandler), # stats after finishing tounrament
    # character stats and items
    ('/char/', CharHandler), # stats editing
    ('/items/', ItemsHandler), # inventory

    ('/battle/', BattleHandler), # evething for battles
    ('/garden/', GardenHandler), # evething for ogorod
], debug=True)