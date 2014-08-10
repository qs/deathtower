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
import json
from random import randint

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
        tvals['randsix'] = randint(1, 6)
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
            kick_skill = Skill.query(Skill.name==u"Двинуть").get()
            if not kick_skill:
                kick_skill = Skill(name=u"Двинуть")
                kick_skill_key = kick_skill.put()
            else:
                kick_skill = kick_skill
                kick_skill_key = kick_skill.key
            char = Char(user=self.user, name=name, skills=[kick_skill_key, ])
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
            tour.chars_alive = tour.chars
            tour.put()
        self.redirect('/tour/')


class RoomHandler(BaseHandler):
    def get(self):
        if self.char.battle:
            self.redirect('/battle/')
        if self.char.room:
            if len(self.char.tour.chars_alive) == 1:
                self.redirect('/final/')
            room = self.char.room.get()
            self.render('room', {'room': room})
        else:
            self.redirect('/tour/')

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
            curr_char = self.char
            char_to_fight = Char.getone(int(escape(self.request.get('room_fight_id'))))
            chars_in_battle = [char_to_fight.key, self.char.key]
            if char_to_fight.battle:
                battle_id = char_to_fight.battle
            else:
                battle_id = Battle.generate_new(chars=chars_in_battle, room=self.char.room)
            battle = battle_id.get()
            if not curr_char in battle.chars:
                battle.chars += [curr_char,]
                battle.chars_alive += [curr_char,]
                battle.put()
            curr_char.battle_turn = (battle.get().current_turn + 1) if battle.get().current_turn > 1 else battle.get().current_turn
            curr_char.battle = battle_id
            curr_char.put()
            self.redirect('/battle/')
        elif self.request.get('room_item'):
            item_pickup = Item.getone(int(escape(self.request.get('room_item_id'))))
            self.char.pick_up_item(item_pickup.key)
            self.redirect('/room/')

class FinalHandler(BaseHandler):
    def get(self):
        tour = self.char.tour
        if len(self.char.tour.chars_alive) == 1:
            exp = 10
            stats = {'winner': self.char, 'tour': tour, 'exp': exp}
            self.char.exp += exp
            tour.win(self.char)
        # show stats after final battle finishing tournament
        self.render('final', stats)


class CharHandler(BaseHandler):
    def get(self):
        # character screen, stats
        if self.char.battle:
            self.redirect('/battle/')
        self.render('char', {'char': self.char})

    def post(self):
        # update stats
        if self.request.get('stat_add_type'):
            stat_type = escape(self.request.get('stat_add_type'))
            if self.char.attrs['free_pts'] > 0:
                self.char.attrs[stat_type] += 1
                self.char.attrs['free_pts'] -= 1
                if stat_type == 'con' and self.char.attrs['con'] % 2 == 0:
                    self.char.attrs['hp_max'] += 1
                    self.char.attrs['hp'] += 1
                self.char.put()
        self.redirect('/char/')


class ItemsHandler(BaseHandler):
    def get(self):
        if self.char.battle:
            self.redirect('/battle/')
        items = self.char.get_items()
        self.render('items', {'items': items})

    def post(self):
        # use item, put on, take off item, drop down
        if self.request.get('item_drop'):
            item = Item.getone(int(escape(self.request.get('item_id'))))
            char = self.char
            room = self.char.room.get()
            if room:
                room.items += [item.key, ]
                room.put()
            for i in xrange(0, len(char.items)):
                if char.items[i] == item.key:
                    char.items.pop(i)
                    char.put()
                    break
        elif self.request.get('item_puton'):
            item = Item.getone(int(escape(self.request.get('item_id'))))
            self.char.puton_item(item.key)
        elif self.request.get('item_takeoff'):
            item = Item.getone(int(escape(self.request.get('worn_id'))))
            self.char.takeoff_item(item.key)
        self.redirect('/items/')


class BattleHandler(BaseHandler):
    def get(self):
        # compose your turn, wait for others
        if self.char.battle:
            # check if battle is ready to compute turns
            battle = self.char.battle.get()
            chars = [ch.get() for ch in battle.chars_alive]
            skills = [s for s in self.char.skills]
            if self._all_chars_turn_done(battle):
                battle.compute_turn()
                if battle.status == BATTLE_FINISHED:
                    self.redirect('/room/')
                else:
                    self.render('battle', {'battle': battle, 'chars': chars, 'skills': skills})
            else:
                self.render('battle', {'battle': battle, 'chars': chars, 'skills': skills})
        else:
            self.redirect('/room/')

    def post(self):
        # char if everyone compose turn compute turns
        if self.request.get('turn_action'):
            battle = self.char.battle.get()
            if self.char.battle_turn == battle.current_turn:
                # compute valid turn
                turn_actions = json.loads(self.request.get('turn_actions'))
                print turn_actions
                person_actions = self._validate_actions(turn_actions)
                if not person_actions:
                    self.redirect('/battle/')
                else:
                    turn_actions = battle.turn_actions
                    turn_actions[self.char.key.id()] = person_actions
                    battle.turn_actions = turn_actions
                    battle.put()
                    self.char.battle_turn += 1
                    self.char.put()
        self.redirect('/battle/')

    def _validate_actions(self, actions):
        ap_left = self.char.attrs['ap']
        person_actions = []
        for a in actions: # turn_actions is a json of {'skill_key', 'aim_key': }
            skill = Skill.getone(int(a['skill']))
            ap_left -= skill.attrs['ap']
            if skill.key not in self.char.skills or ap_left < 0:
                return False
            else:
                person_actions.append(a)
        return person_actions

    def _all_chars_turn_done(self, battle):
        chars_turn = min([ch.get().battle_turn for ch in battle.chars_alive])
        if chars_turn > battle.current_turn:
            return True
        else:
            return False

class GardenHandler(BaseHandler):
    def get(self):
        garden = self.char.garden
        if not garden:
            Garden.generate(self.char)
            self.redirect('/garden/')
        garden = self.char.garden
        plants, already_items = garden.get_visited()
        seeds = [i for i in self.char.items if i.get() and i.get().type == ITEM_SEED]
        # plants, fruits
        self.render('garden', {'plants': plants, 'already_items': already_items, 'seeds': seeds})

    def post(self):
        if self.request.get('seed'):
            seed = Item.getone(int(escape(self.request.get('seed_id'))))
            if self.char.garden:
                garden = self.char.garden
                garden.plant_smth(seed)

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