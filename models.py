#!/usr/bin/env python
# coding:utf-8
import random
import datetime
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
ITEM_SEED = 5 # a seed, for use in garden

ITEM_TYPES = [ITEM_MISC, ITEM_HAND, ITEM_BODY, ITEM_HEAD, ITEM_DRINK, ITEM_SEED]

DEFAULT_CHAR_ATTRS = {
    'hp': 10,
    'hp_max': 10,
    'dmg': 1,
    'spd': 5,
    'ap': 10,
    'str': 1,
    'dex': 1,
    'con': 1,
    'int': 1,
    'free_pts': 3
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

PLANT_ARMOR = ITEM_BODY
PLANT_WEAPON = ITEM_HAND
PLANT_BOTTLE = ITEM_DRINK
DEFAULT_PLANT_DURATION = ITEM_DRINK


# temp demo data
ROOM_GRAPH = {
    u'Комнатка Самоубийсв': {'dirs': [u'Холл Безнадежности', u'Коридор Тлена'], 'desrc': u""},
    u'Прачечная Совести': {'dirs': [u'Холл Безнадежности', u'Коридор Тлена'], 'desrc': u""},
    u'Коридор Тлена': {'dirs': [u'Прачечная Совести', u'Столовая Безжизненности'], 'desrc': u'Кабинет Сожалений'},
    u'Холл Безнадежности': {'dirs': [u'Комнатка Самоубийсв', u'Кабинет Сожалений'], 'desrc': u""},
    u'Кабинет Сожалений': {'dirs': [u'Столовая Безжизненности', u'Коридор Тлена'], 'desrc': u""},
    u'Столовая Безжизненности': {'dirs': [u'Прачечная Совести', u'Комнатка Самоубийсв'], 'desrc': u""},
}

ITEM_NAMES = {ITEM_HEAD: [u'Шлем', u'Жуткий шлем'],
                ITEM_BODY: [u'Доспех радости', u'Доспех дня'],
                ITEM_HAND: [u'Дубинка радости', u'Букет', u'Меч'],
                ITEM_DRINK: [u'Лечилка', u'Мега-лечилка'],
                ITEM_SEED: [u'Семечко подсолнуха', u'Красивое семечко'],
                ITEM_MISC: [u'Интереснейший хлам', u'Эссенция бесполезности']}

ITEM_ATTRS = {ITEM_HEAD: 'res_dmg',
                ITEM_BODY: 'res_dmg',
                ITEM_HAND: 'dmg',
                ITEM_DRINK: 'hp',
                ITEM_SEED: 'type',
                ITEM_MISC: 'type'}


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
    room = ndb.KeyProperty()  # Room in tournament
    battle_turn = ndb.IntegerProperty(default=1)

    @classmethod
    def get_char_by_user(cls, user):
        char = cls.query(cls.user==user).get()
        return char

    def get_add_patk(self):
        dmg = 0
        for e in self.effects:
            dmg += e.get().attrs.get('dmg')
        for w in self.worns:
            if w.get().type == 'item_hand':
                dmg += w.get().attrs.get('dmg')
        return dmg

    def fight(self, target, skill):
        dmg = 1 + self.attrs['str'] / 2 + self.get_add_patk()
        is_crit = True if random.randint(1, 100) in range(1, 5 * (self.attrs['dex'] / 2) + 1) else False
        target.acc_dmg(dmg, is_crit)

    def lose(self):
        room = self.room.get()
        for i in self.items:
            if not i.get().type == ITEM_SEED:
                room.items.append(i)
        battle = self.battle.get()
        battle.lose(self)
        battle.put()
        tour = self.tour.get()
        tour.lose(self)
        tour.put()
        self.battle = None
        self.tour = None
        self.room = None
        self.battle_turn = None
        self.items = [i for i in self.items if i.get().type == ITEM_SEED]
        self.attrs['hp'] = self.attrs['hp_max']
        self.put()

    def acc_dmg(self, dmg, is_crit):
        if self.battle:
            me_crit = True if random.randint(1, 100) in range(1, 5 * (self.attrs['dex'] / 2) + 1) else False
            mod = 2 if is_crit and not me_crit else 1
            mod = 0.5 if me_crit and not is_crit else mod
            self.attrs['hp'] -= int(dmg * mod)
            self.put()
            if self.attrs['hp'] <= 0:
                self.lose()

    def get_skills(self):
        return [s.get() for s in self.skills]

    def get_items(self):
        return [i.get() for i in self.items]

    def get_worns(self):
        return [i.get() for i in self.worns]

    def pick_up_item(self, item_key):
        room = self.room.get()
        print item_key, room.items
        if item_key not in room.items:
            return False  # no item in this room
        room.items.remove(item_key)
        room.put()
        self.items.append(item_key)
        self.put()
        return True

    def drop_down_item(self, item_key):
        room = self.room.get()
        if item_key not in self.items:
            return False  # no item in inventory
        self.items.remove(item_key)
        self.put()
        room.items.append(item_key)
        room.put()
        return True

    def puton_item(self, item_key):
        item = item_key.get()
        if item.type in [ITEM_MISC, ITEM_DRINK, ITEM_SEED]:
            return False
        if item_key not in self.items:
            return False  # no item in inventory
        witems = [i for i in self.get_worns() if i.type == item.type]
        if len(witems) > 0:
            self.worns.remove(witems[0].key)
            self.items.append(witems[0].key)
        self.worns.append(item_key)
        self.items.remove(item_key)
        self.put()

    def takeoff_item(self, item_key):
        if item_key not in self.worns:
            return False  # no item on person
        self.worns.remove(item_key)
        self.items.append(item_key)
        self.put()
        return True

    @property
    def garden(self):
        return Garden.query(Garden.char == self.key).get()


class CharEffect(BaseModel):
    effect = ndb.KeyProperty(required=True)
    finish_turn = ndb.IntegerProperty(required=True, default=1)
    char = ndb.KeyProperty(required=True)

    def check_effect(self):
        if self.battle.current_turn >= self.finish_turn:
            self.disable_effect()

    def disable_effect(self):
        self.key.delete()

class Effect(BaseModel):
    name = ndb.StringProperty(required=True)
    attrs = ndb.JsonProperty(default=[])#here 'type':'bad' or 'good'


class Skill(BaseModel):
    name = ndb.StringProperty(required=True)
    attrs = ndb.JsonProperty(default=DEFAULT_SKILL_ATTRS)


class Item(BaseModel):
    name = ndb.StringProperty(required=True)
    type = ndb.IntegerProperty(required=True,
            default=ITEM_MISC,
            choices=ITEM_TYPES)
    attrs = ndb.JsonProperty(default=[])

    @classmethod
    def generate(self, item_type, char=None, item_name=None):
        if not item_name:
            item_name = ITEM_NAMES[item_type][random.randint(0, len(ITEM_NAMES[item_type])-1)]
        new_item = Item(name=item_name, type=item_type)
        special_attr = ITEM_ATTRS[item_type]
        new_item.attrs = {special_attr: 1}
        if u'ега' in item_name:
            new_item.attrs = {special_attr: 3}
        new_item_id = new_item.put()
        new_item = new_item_id.get()
        if char:
            char = char.get()
            char.items = char.items + [new_item.key,]
            char.put()
        return new_item

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
            tour.upd_chars()
        return cnt, tours

    def upd_chars(self):
        self.chars_obj = [ch.get() for ch in self.chars]

    def win(self, pers):
        if len(self.chars_alive) <= 1:
            self.finish_dt = datetime.datetime.now()
            pers.tour = None
            pers.room = None
            pers.battle_turn = None
            pers.put()

    def lose(self, pers):
        self.chars_alive = [c for c in self.chars_alive if c != pers.key]
        self.put()
        if len(self.chars_alive) <= 1:
            winner = self.chars_alive[0].get()
            self.win(winner)
            winner.battle = None
#            winner.tour = None
#            winner.room = None
#            winner.battle_turn = None
            winner.put()

    def start_tour(self):
        # update status
        self.status = TOUR_PROGRESS
        self.put()
        # create rooms if nessesary
        q = Room.query()
        room_cnt = q.count()
        if room_cnt == 0:
            room_keys = {}
            for room_name in ROOM_GRAPH.keys():
                room = Room(name=room_name)
                room_key = room.put()
                room_keys[room_name] = room_key
        else:
            room_keys = dict([(r.name, r.key) for r in q])
        for room_name, room_data in ROOM_GRAPH.items():
            room = Room.query(Room.name==room_name).get()
            room.dirs = [room_keys[r] for r in room_data['dirs']]
            room.put()
        # place chars
        for ch in self.chars:
            char = ch.get()
            char.room = random.choice(room_keys.values())
            char.put()
        # place items
        items = []
        for i in range(room_cnt * 2):
            item = Item.generate(random.choice(ITEM_TYPES))
            items.append(item)
        rooms = [r.get() for r in room_keys.values()]
        for i in items:
            random.choice(rooms).items.append(i.key)
        for room in rooms:
            room.put()


class Room(BaseModel):  # tournament session room
    name = ndb.StringProperty(required=True)
    items = ndb.KeyProperty(repeated=True) # list of Item
    dirs = ndb.KeyProperty(repeated=True)  # keys of rooms to go

    def get_dirs(self):
        return [r.get() for r in self.dirs]

    def get_items(self):
        return [i.get() for i in self.items]

    def get_chars(self):
        return Char.query(Char.room == self.key)


class Garden(BaseModel):  # tournament session room
    char = ndb.KeyProperty(required=True)  # owner
    attrs = ndb.JsonProperty(default=[])  # size, filled, watered
    plants = ndb.JsonProperty(default=[])  # plants, their fruits and dt of riping

    def get_visited(self):
        Item.generate(ITEM_SEED, self.char, u'Semka')
        all_plants = Plant.query(Plant.garden == self.key)
        plants = []
        already_items = []
        now = datetime.datetime.now()
        for plant in all_plants:
            if now >= plant.finish_dt:
                fruit = plant.get_fruit()
                already_items.append(fruit)
            else:
                plants.append(plant)
        return plants, already_items

    def plant_smth(self, seed):
        if seed.type == ITEM_SEED:
            pl = Plant()
            pl.name = u'Растение'
            pl.type = [PLANT_ARMOR, PLANT_WEAPON, PLANT_BOTTLE][random.randint(0,2)]
            pl.garden = self.key
            pl.dt = datetime.datetime.now()
            pl.put()
            self.plants = self.plants + [pl.key,]
            seed.key.delete()

    @classmethod
    def generate(cls, char):
        new_garden = Garden(**{'char': char.key})
        new_garden.put()

class Plant(BaseModel):
    name = ndb.StringProperty(required=True)
    type = ndb.IntegerProperty(required=True,
            default=PLANT_ARMOR,
            choices=[PLANT_ARMOR, PLANT_WEAPON, PLANT_BOTTLE])
    garden = ndb.KeyProperty(required=True)
    dt = ndb.DateTimeProperty(auto_now_add=True)
    finish_dt = ndb.DateTimeProperty(default=datetime.datetime.now() + datetime.timedelta(minutes=DEFAULT_PLANT_DURATION))

    def get_fruit(self):
        now = datetime.datetime.now()
        if self.finish_dt <= now:
            new_item = Item.generate(self.type, self.garden.get().char)
            new_item.put()
            self.key.delete()
            return new_item


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
    turn_actions = ndb.JsonProperty(default={}) # empty every new turn, sort after all do actions

    def lose(self, pers):
        self.chars_alive = [c for c in self.chars_alive if c != pers.key]
        self.put()
        if len(self.chars_alive) <= 1:
            winner = self.chars_alive[0].get()
            winner.battle = None
            winner.battle_turn = None
            winner.attrs['hp'] = winner.attrs['hp_max']
            winner.put()

    @classmethod
    def generate_new(self, chars, room):
        battle = Battle(**{'chars': chars, 'chars_alive': chars, 'room': room})
        battle_key = battle.put()
        for c in chars:
            char = c.get()
            char.battle = battle_key
            char.battle_turn = 1
            char.put()
        return battle_key

    def compute_turn(self):
        chars = sorted([ch.get() for ch in self.chars_alive], key=lambda x: x.attrs['spd'], reverse=True)
        turn_actions = self.turn_actions
        for ch in chars:
            if unicode(ch.key.id()) in turn_actions:
                acts = turn_actions.pop(unicode(ch.key.id()))
                for a in acts:
                    skill = Skill.getone(int(a['skill']))
                    target = Char.getone(int(a['aim']))
                    ch.fight(target, skill)
                    if (self.chars_alive) == 1:
                        break
        self.current_turn += 1
        self.turn_actions = {}
        self.put()
