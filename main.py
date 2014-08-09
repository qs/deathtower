#!/usr/bin/env python
# coding:utf-8

import webapp2
import jinja2
import os
import json
from cgi import escape
from models import *
from datetime import datetime, timedelta
from google.appengine.api import users


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class BaseHandler(webapp2.RequestHandler):
    def __init__(self, request, response):
        self.initialize(request, response)
        self.user = users.get_current_user()
        self.char = Char.get_char_by_user(self.user) if self.user else None

    def render(self, tpl_file, tvals={}):
        tvals['logout'] = users.create_logout_url("/")
        tvals['char'] = self.char
        tpl = jinja_environment.get_template('templates/' + tpl_file + '.html')
        self.response.out.write(tpl.render(tvals))

    def render_json(self, data):
        self.response.out.write(json.dumps(data))

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)


class WelcomeHandler(BaseHandler):
    def get(self):
        self.render('welcome')


class JoinHandler(BaseHandler):
    def get(self):
        # check if char exists, character creation screen
        if self.char:  # you already have char!
            self.redirect('/tour/')
        self.render('join')

    def post(self):
        # create character
        if self.request.get('char_add'):
            name = escape(self.request.get('char_name'))
            char = Char(user=self.user, name=name)
            char.put()
            self.redirect('/tour/')
        else:
            self.redirect('/join/')


class TourHandler(BaseHandler):
    def get(self):
        # list for tounaments
        if self.char.tour:
            # temp check if time to start tournament
            tour = self.char.tour.get()
            tour.upd_chars()
            if tour and tour.start_dt <= datetime.now():
                print tour.start_dt, datetime.now()
                tour.start_tour() # place rooms, items, chars, update status
                self.redirect('/room/')
            # not showing list if char already choose tour
            tours_cnt = 1
            tours = [tour, ] if tour else []
        else:
            tours_cnt, tours = Tour.get_tour_requests()
        self.render('tour', {'tours': tours, 'tours_cnt': tours_cnt})

    def post(self):
        # join or create tournament request
        if self.request.get('tour_add'):
            # create new tour
            tour_lvl = int(escape(self.request.get('tour_level')))
            if tour_lvl == 0:
                level_min = 1
                level_max = 99
            elif tour_lvl == 1:
                level_min = self.char.level - 1
                level_max = self.char.level + 1
            else:
                level_min = self.char.level
                level_max = self.char.level
            tour_start = int(escape(self.request.get('tour_start')))
            start_dt = datetime.now() + timedelta(minutes=tour_start)
            tour = Tour(level_min=level_min, level_max=level_max,
                        chars=[self.char.key, ], start_dt=start_dt)
            tour_key = tour.put()
            self.char.tour = tour_key
            self.char.put()
        elif self.request.get('tour_join'):
            # join existing tour
            tour = Tour.getone(int(escape(self.request.get('tour_join_id'))))
            self.char.tour = tour.key
            self.char.put()
            tour.chars.append(self.char.key)
            tour.put()
        self.redirect('/tour/')


class RoomHandler(BaseHandler):
    def get(self):
        room = self.char.room.get()
        self.render('room', {'room': room})

    def post(self):
        if self.request.get('room_move'):
            room_move = Room.getone(int(escape(self.request.get('room_move_id'))))
            room = self.char.room.get()
            if room_move.key in room.dirs:
                self.char.room = room_move.key
                self.char.put()
            # move to another room, attack person or pickiu item
            self.redirect('/room/')
        elif self.request.get('room_fight'):
            char_to_fight = Char.getone(int(escape(self.request.get('room_fight_id'))))
            battle = char_to_fight.battle if char_to_fight.battle else Battle.generate_new(chars=[char_to_fight, self.char])


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
        garden = self.char.garden
        plants, already_items = garden.get_visited()
        seeds = [i for i in self.char.items if i.type == ITEM_SEED]
        # plants, fruits
        self.render('garden', {'plants': plants, 'already_items': already_items, 'seeds': seeds})

    def post(self):
        # watering plants, puck up fruits, remove plant
        self.redirect('/garden/')


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
    ('/garden/', GardenHandler), # evething for ogorod
], debug=True)