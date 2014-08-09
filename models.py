#!/usr/bin/env python
# coding:utf-8
from google.appengine.ext import ndb

TOUR_NEW = 0
TOUR_PROGRESS = 1
TOUR_FINISHED = 2

BATTLE_PROGRESS = 1
BATTLE_FINISHED = 2

DEFAULT_CHARACTER_ATTRS = {
    'hp': 100,
    'hp_max': 100,
    'dmg': 3,
    'spd': 5,
    'ap': 10
}

class BaseModel(ndb.Model):
    @classmethod
    def getone(c, key_name):
        k = ndb.Key(c, key_name)
        return k.get()

    @property
    def id(self):
        return self.key.id()


class Char(BaseModel):
    user = ndb.UserProperty(required=True)
    dt = ndb.DateTimeProperty(auto_now_add=True)
    name = ndb.StringProperty(required=True)
    attrs = ndb.JsonProperty(default=DEFAULT_CHARACTER_ATTRS)
    items = ndb.KeyProperty(repeated=True)
    action_timeout = ndb.DateTimeProperty(auto_now_add=True)  # can't do anything if this > dt.now()

class Item(BaseModel):
    name = ndb.StringProperty(required=True)
    attrs = ndb.JsonProperty(default=[])


class Tour(BaseModel):
    dt = ndb.DateTimeProperty(auto_now_add=True)  # request dt
    start_dt = ndb.DateTimeProperty(required=True)  # tournament starts
    finish_dt = ndb.DateTimeProperty()  #
    status = ndb.IntegerProperty(required=True,
            default=TOUR_NEW,
            choices=[TOUR_NEW, TOUR_PROGRESS, TOUR_FINISHED])
    chars = ndb.KeyProperty(repeated=True)
    chars_alive = ndb.KeyProperty(repeated=True)


class Room(BaseModel):  # tournament session room
    name = ndb.StringProperty(required=True)
    items = ndb.KeyProperty(repeated=True)
    dirs = ndb.KeyProperty(repeated=True)  # keys of rooms to go


class Garden(BaseModel):  # tournament session room
    char = ndb.KeyProperty(required=True)  # owner
    attrs = ndb.JsonProperty(default=[])  # size, filled, watered
    plants = ndb.JsonProperty(default=[])  # plants, their fruits and dt of riping


class Battle(BaseModel):
    dt = ndb.DateTimeProperty(auto_now_add=True)  # request dt
    finish_dt = ndb.DateTimeProperty()  #
    current_turn = ndb.IntegerProperty(required=True, default=1)
    status = ndb.IntegerProperty(required=True,
            default=BATTLE_PROGRESS,
            choices=[BATTLE_PROGRESS, BATTLE_FINISHED])
    chars = ndb.KeyProperty(repeated=True)
    chars_alive = ndb.KeyProperty(repeated=True)

