#!/usr/bin/env python
# coding:utf-8
from google.appengine.ext import ndb

TOUR_NEW = 0
TOUR_PROGRESS = 1
TOUR_FINISHED = 2

BATTLE_PROGRESS = 1
BATTLE_FINISHED = 2

ITEM_MISC = 0  # mock item, nothing to do with this just drop
ITEM_HAND = 1  # can put on hand (weapon)
ITEM_BODY = 2  # can wear on body (armor)
ITEM_HEAD = 3  # can wear on head (helmet)
ITEM_DRINK = 4  # can use for effect

ITEM_TYPES = [ITEM_MISC, ITEM_HAND, ITEM_BODY, ITEM_HEAD, ITEM_DRINK]

DEFAULT_CHAR_ATTRS = {
    'hp': 100,
    'hp_max': 100,
    'dmg': 3,
    'spd': 5,
    'ap': 10
}

DEFAULT_SKILL_ATTRS = {
    'dmg': 3,
    'ap': 3,
    'req_str': 1,
    'req_dex': 1,
    'req_con': 1,
    'req_int': 1,
}

DEFAULT_TOUR_ATTRS = {
}


ROOM_GRAPH = {
    u'Комнатка Самоубийсв': {'dirs': [u'Холл Безнадежности', u''], 'desrc': u""},
    u'Прачечная Совести': {'dirs': [u'Холл Безнадежности', u'Коридор Тлена'], 'desrc': u""},
    u'Коридор Тлена': {'dirs': [u'Прачечная Совести', u'Столовая Безжизненности'], 'desrc': u'Кабинет Сожалений'},
    u'Холл Безнадежности': {'dirs': [u'Комнатка Самоубийсв', u'Кабинет Сожалений'], 'desrc': u""},
    u'Кабинет Сожалений': {'dirs': [u'Столовая Безжизненности', u'Коридор Тлена'], 'desrc': u""},
    u'Столовая Безжизненности': {'dirs': [u'Прачечная Совести', u'Комнатка Самоубийсв'], 'desrc': u""},
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
    attrs = ndb.JsonProperty(default=DEFAULT_CHAR_ATTRS)
    level = ndb.IntegerProperty(default=1)
    exp = ndb.IntegerProperty(default=0)
    items = ndb.KeyProperty(repeated=True)  # list of Item that are in inventory
    worns = ndb.KeyProperty(repeated=True)  # list of Item that are on char
    action_timeout = ndb.DateTimeProperty(auto_now_add=True)  # can't do anything if this > dt.now()
    battle = ndb.KeyProperty()  # Battle key, where char take place
    tour = ndb.KeyProperty()  # Tour key, where char take place
    skills = ndb.KeyProperty(repeated=True)  # list of Skill
    effects = ndb.KeyProperty(repeated=True)  # list of CharEffect

    @classmethod
    def get_char_by_user(cls, user):
        char = cls.query(cls.user==user).get()
        return char


class CharEffect():
    effect = ndb.KeyProperty(required=True)
    finish_turn = ndb.IntegerProperty(required=True, default=1)


class Effect():
    name = ndb.StringProperty(required=True)
    attrs = ndb.JsonProperty(default=[])


class Skill():
    name = ndb.StringProperty(required=True)
    attrs = ndb.JsonProperty(default=DEFAULT_SKILL_ATTRS)


class Item(BaseModel):
    name = ndb.StringProperty(required=True)
    type = ndb.IntegerProperty(required=True,
            default=ITEM_MISC,
            choices=ITEM_TYPES)
    attrs = ndb.JsonProperty(default=[])


class Tour(BaseModel):
    dt = ndb.DateTimeProperty(auto_now_add=True)  # request dt
    start_dt = ndb.DateTimeProperty(required=True)  # tournament starts
    finish_dt = ndb.DateTimeProperty()
    status = ndb.IntegerProperty(required=True,
            default=TOUR_NEW,
            choices=[TOUR_NEW, TOUR_PROGRESS, TOUR_FINISHED])
    attrs = ndb.JsonProperty(default=DEFAULT_TOUR_ATTRS)
    level_min = ndb.IntegerProperty(default=1)
    level_max = ndb.IntegerProperty(default=99)
    chars = ndb.KeyProperty(repeated=True)
    chars_alive = ndb.KeyProperty(repeated=True)

    @classmethod
    def get_tour_requests(cls):
        q = cls.query(cls.status==TOUR_NEW)
        cnt = q.count()
        tours = q.order(Tour.start_dt)
        for tour in tours:
            tour.chars_obj = [ch.get() for ch in tour.chars]
        return cnt, tours

    def start_tour(self):
        # update status
        self.status = TOUR_PROGRESS
        self.put()
        # create rooms if nessesary
        q = Room.query()
        if q.count() == 0:
            room_keys = {}
            for room_name in ROOM_GRAPH.keys():
                room = Room(name=room_name)
                room_key = room.put()
                room_keys[room_name] = room_key
            for room_name, room_data in ROOM_GRAPH.items():
                room = Room.query(Room.name==room_name)
                room.dirs = [room_keys[r] for r in room_data['dirs']]
                room.put()
        # place chars

        # place items


class Room(BaseModel):  # tournament session room
    name = ndb.StringProperty(required=True)
    items = ndb.KeyProperty(repeated=True) # list of Item
    dirs = ndb.KeyProperty(repeated=True)  # keys of rooms to go
    chars = ndb.KeyProperty(repeated=True)  # list of Char


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
    room = ndb.KeyProperty()
