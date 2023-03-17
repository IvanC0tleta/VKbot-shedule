import requests
from bs4 import BeautifulSoup
import datetime
import re

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from pymongo import MongoClient

vk_session = vk_api.VkApi(token=open('token.txt', 'r', encoding='UTF-8').read())

client = MongoClient(open('mongodbClient.txt', 'r', encoding='UTF-8').read())
db = client.botosu

pattern_date = r'\d\d[.]\d\d'
pattern_full_date = r'\d\d[.]\d\d[.]\d\d\d\d'

START_KEYBOARD = VkKeyboard(one_time = True)
START_KEYBOARD.add_button('Начать', VkKeyboardColor.POSITIVE)

GET_WHO_KEYBOARD = VkKeyboard(one_time = True)
GET_WHO_KEYBOARD.add_button('Студент', VkKeyboardColor.POSITIVE)
GET_WHO_KEYBOARD.add_button('Преподаватель', VkKeyboardColor.POSITIVE)

MENU_KEYBOARD = VkKeyboard()
MENU_KEYBOARD.add_button('Сегодня', VkKeyboardColor.POSITIVE)
MENU_KEYBOARD.add_button('Завтра', VkKeyboardColor.POSITIVE)
MENU_KEYBOARD.add_line()
MENU_KEYBOARD.add_button('Справка', VkKeyboardColor.PRIMARY)
MENU_KEYBOARD.add_button('Заново', VkKeyboardColor.SECONDARY)

FACULT_KEYBOARD = VkKeyboard(one_time = True)

POTOK_KEYBOARD = VkKeyboard(one_time = True)

GROUP_KEYBOARD = VkKeyboard(one_time = True)

class User:
    def __init__(self, user_id):
        self.user = db.users.find_one({'_id': user_id})
        self.id = self.user['_id']
        self.who = self.user['who']
        self.faculty = self.user['faculty']
        self.potok = self.user['potok']
        self.group = self.user['group']

    def set_who(self, who):
        db.users.update_one({'_id': self.id}, {'$set': {'who': who}})

    def is_set_who(self):
        return self.who is None

    def set_faculty(self, faculty):
        db.users.update_one({'_id': self.id}, {'$set': {'faculty': faculty}})

    def is_set_faculty(self):
        return self.faculty is None

    def set_potok(self, potok):
        db.users.update_one({'_id': self.id}, {'$set': {'potok': potok}})

    def is_set_potok(self):
        return self.potok is None

    def set_group(self, group):
        db.users.update_one({'_id': self.id}, {'$set': {'group': group}})

    def is_set_group(self):
        return self.group is None

    def delete(self):
        db.users.delete_one({'_id': self.id})

    @staticmethod
    def create(user_id):
        db.users.insert_one({
            '_id': user_id,
            'who': None,
            'faculty': None,
            'potok': None,
            'group': None
        })


def get_faculty(faculty, who):
    if who == 1:
        data = {
            'who': '1',
            'request': 'facult',
            'filial': '1',
        }
    else:
        data = {
            'who': '2',
            'request': 'facult',
            'filial': '1',
        }
    headers = {
        'X-Requested-With': 'XMLHttpRequest'
    }
    url = 'http://www.osu.ru/pages/schedule/index.php'
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        ev = eval(response.text)
        for x in ev['list']:
            if x['name'].lower() == faculty.lower():
                return x['id']
    return None


def get_potok(faculty, potok, who):
    if who == 1:
        data = {
            'who': '1',
            'what': '1',
            'request': 'potok',
            'filial': '1',
            'mode': 'full',
            'facult': faculty
        }
    else:
        data = {
            'who': '2',
            'what': '1',
            'request': 'kafedra',
            'filial': '1',
            'mode': 'full',
            'facult': faculty
        }

    headers = {
        'X-Requested-With': 'XMLHttpRequest'
    }
    response = requests.post(url='http://www.osu.ru/pages/schedule/index.php', data=data, headers=headers)
    if response.status_code == 200:
        ev = eval(response.text)
        for x in ev['list']:
            if x['name'].lower().find(potok) != -1:
                return x['id']
    return None


def get_group(faculty, potok, group, who):
    if who == 1:
        data = {
            'who': '1',
            'what': '1',
            'request': 'group',
            'filial': '1',
            'mode': 'full',
            'facult': faculty,
            'potok': potok
        }
    else:
        data = {
            'who': '2',
            'what': '1',
            'request': 'prep',
            'filial': '1',
            'mode': 'full',
            'facult': faculty,
            'kafedra': potok
        }

    headers = {
        'X-Requested-With': 'XMLHttpRequest'
    }
    response = requests.post(url='http://www.osu.ru/pages/schedule/index.php', data=data, headers=headers)
    if response.status_code == 200:
        ev = eval(response.text)
        for x in ev['list']:
            if x['name'].lower().replace(" ","") == group.lower().replace(" ", ""):
                return x['id']
    return None


def slot(group, date, who):
    if who == 1:
        data = {
            'who': '1',
            'what': '1',
            'request': 'rasp',
            'filial': '1',
            'group': group,
            'mode': 'full'
        }
    else:
        data = {
            'who': '2',
            'what': '1',
            'request': 'rasp',
            'filial': '1',
            'prep': group,
            'mode': 'full'
        }
    url = 'http://www.osu.ru/pages/schedule/index.php'
    response = requests.post(url, data=data)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'lxml')
        table = soup.find('table')
        tr = table.find(lambda tag: tag.text.find(date) != -1, recursive=False)
        pars = []
        if tr:
            for td in tr:
                if td.get('class'):
                    if td['class'][0] == 'asd':
                        pars.append({td.table.tr.td['pare_id']: re.sub(pattern_full_date, '',
                                                                       td.text.replace('(практическое занятие)',
                                                                                       ' ').replace('ОФК', '\nОФК'))})
                if td.get('pare_id'):
                    pars.append({
                        td.get('pare_id'): re.sub(pattern_full_date, '', td.text)
                    })
            if len(pars) > 0:
                result_string = ""
                calls_soup = soup.find(id='tableheader')
                calls = {}
                for call in calls_soup:
                    key = '0'
                    val = '0'
                    for current in call.strings:
                        if current.lower().find("пара") != -1:
                            key = current[0]
                        elif current.lower().find("дата") == -1:
                            val = current
                    calls[key] = val
                for dic in pars:
                    for n, s in dic.items():
                        result_string = result_string + n + " пара " + calls[n] + "\n" + s + '\n\n'
                return date + "\n\n" + result_string
            else:
                return ("На выбранную дату нет расписания.")
        else:
            return ("Неверный формат ввода. Повторите ваш запрос.")
    else:
        return ("Расписание недоступно. Повторите запрос позже.")


def request(day, user):
    if day == 1:
        day = datetime.datetime.now().strftime("%d.%m.%Y")
    elif day == 2:
        day = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    elif re.match(pattern_date, day) and len(day) == 5:
        day = day + datetime.datetime.now().strftime(".%Y")

    return slot(user.group, day, user.who)


def main():
    mes_info = open('info.txt', 'r', encoding="utf-8").read()
    mes_repeat_request = " Попробуйте еще раз.\n<<?>> или <<справка>> - получить справку."
    for event in VkLongPoll(vk_session).listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
            user_id = event.user_id
            text = event.text.lower()
            if text == "начать":
                send_message(user_id, open('start_text.txt', 'r', encoding="utf-8").read())
            if db.users.count_documents({'_id': user_id}) == 0:
                User.create(event.user_id)
                send_message(user_id, "Напишите или выберете кто вы:  <<Студент>> или <<Преподаватель>>", GET_WHO_KEYBOARD.get_keyboard())
                continue


            user = User(user_id)
            
            if text == "заново" or text == "3" or text == "з":
                user.delete()
                send_message(user_id, "Отправь <<Начать>>", START_KEYBOARD.get_keyboard())
                continue
            if text == "?" or text == "справка":
                send_message(user_id, mes_info)
                continue

            
            if user.is_set_who():
                get_keyboard_facult()
                if text == "студент":
                    user.set_who(1)
                    send_message(user_id, "Напишите  факультет, например <<ФМИТ>>", FACULT_KEYBOARD.get_keyboard())
                elif text == "преподаватель":
                    user.set_who(2)
                    send_message(user_id, "Напишите факультет, например <<ФМИТ>>", FACULT_KEYBOARD.get_keyboard())
                else:
                    send_message(user_id, mes_repeat_request, GET_WHO_KEYBOARD.get_keyboard())
                continue

            if user.is_set_faculty():
                if get_faculty(text, user.who):
                    user.set_faculty(get_faculty(text, user.who))
                    get_keyboard_potok(get_faculty(text, user.who), user.who)
                    if user.who == 1:
                        send_message(user_id, "Теперь напишите номер курса в числовом формате, например <<2>>", POTOK_KEYBOARD.get_keyboard())
                    else:
                        send_message(user_id, "Теперь напишите вашу кафедру, например <<ГКН>>", POTOK_KEYBOARD.get_keyboard())
                else:
                    send_message(user_id, "Не удалось определить факультет." + mes_repeat_request, FACULT_KEYBOARD.get_keyboard())
                continue
            if user.is_set_potok():
                if get_potok(user.faculty, text, user.who):
                    user.set_potok(get_potok(user.faculty, text, user.who))
                    if user.who == 1:
                        send_message(user_id, "Теперь напишите свою группу, например <<20мкн(б)апкм>>")
                    else:
                        send_message(user_id, "Напишите фамилию и инициалы в формате <<Иванов И.И.>>")
                else:
                    send_message(user_id,
                                 "Не удалось определить курс." + mes_repeat_request,
                                 POTOK_KEYBOARD.get_keyboard()) if user.who == 1 else send_message(user_id,
                                                                                                    "Не удалось определить кафедру." + mes_repeat_request,
                                                                                                    POTOK_KEYBOARD.get_keyboard())
                continue

            if user.is_set_group():
                if get_group(user.faculty, user.potok, text, user.who):
                    user.set_group(get_group(user.faculty, user.potok, text, user.who))
                    send_message(user_id, mes_info, MENU_KEYBOARD.get_keyboard())
                else:
                    send_message(user_id,
                                 "Не удалось определить группу." + mes_repeat_request) if user.who == 1 else send_message(user_id,
                                                                                                                         "Не удалось определить преподавателя." + mes_repeat_request)
                continue

            if text == "сегодня" or text == "1":
                send_message(user_id, request(1, user))
                send_message(user_id, mes_info)
                continue
            elif text == "завтра" or text == "2":
                send_message(user_id, request(2, user))
                send_message(user_id, mes_info)
                continue
            elif re.match(pattern_date, text) and len(text) == 5:
                send_message(user_id, request(text, user))
                send_message(user_id, mes_info)
            else:
                send_message(user_id, "Неизвестная команда." + mes_repeat_request)


def send_message(user_id, message, keyboard=None):
    if keyboard is None:
        vk_session.method("messages.send", {"user_id": user_id,
                                        "message": message,
                                        "random_id": 0})
    else:
        vk_session.method("messages.send", {"user_id": user_id,
                                        "message": message,
                                        "random_id": 0,
                                        "keyboard": keyboard})

def get_keyboard_facult():
    data = {
        'who': '1',
        'request': 'facult',
        'filial': '1',
    }
    headers = {
        'X-Requested-With': 'XMLHttpRequest'
    }
    url = 'http://www.osu.ru/pages/schedule/index.php'
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        ev = eval(response.text)
        col = 0;
        global FACULT_KEYBOARD
        FACULT_KEYBOARD = None
        FACULT_KEYBOARD = VkKeyboard(one_time = True)
        for x in ev['list']:
            if col <= 3:
                FACULT_KEYBOARD.add_button(x['name'])
                col += 1
            else:
                FACULT_KEYBOARD.add_line()
                FACULT_KEYBOARD.add_button(x['name'])
                col = 1
    return None

def get_keyboard_potok(faculty, who):
    if who == 1:
        data = {
            'who': '1',
            'what': '1',
            'request': 'potok',
            'filial': '1',
            'mode': 'full',
            'facult': faculty
        }
    else:
        data = {
            'who': '2',
            'what': '1',
            'request': 'kafedra',
            'filial': '1',
            'mode': 'full',
            'facult': faculty
        }

    headers = {
        'X-Requested-With': 'XMLHttpRequest'
    }
    response = requests.post(url='http://www.osu.ru/pages/schedule/index.php', data=data, headers=headers)
    if response.status_code == 200:
        ev = eval(response.text)
        global POTOK_KEYBOARD
        POTOK_KEYBOARD = None
        POTOK_KEYBOARD = VkKeyboard(one_time=True)
        col = 0
        for x in ev['list']:
            if col < 3:
                POTOK_KEYBOARD.add_button(x['name'])
                col += 1
            else:
                POTOK_KEYBOARD.add_line()
                POTOK_KEYBOARD.add_button(x['name'])
                col = 1
    return None

if __name__ == '__main__':
    main()
