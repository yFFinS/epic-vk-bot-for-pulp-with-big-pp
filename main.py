import json
import os
import random
import threading
import time
import urllib.request

import colorama
import vk_api
from vk_api.bot_longpoll import *

access_token = 'token'
group_id = 'id'
longpoll = None
vk = None
vk_session = None
send_mode = False
traceback_mode = 1
images_cache = set()
messages_cache = set()


def status(func):
    def wrapper(*args, **kwargs):
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            if traceback_mode == 2:
                print(colorama.Style.BRIGHT + colorama.Fore.GREEN
                      + f'{func.__name__} completed in {time.time() - start_time}')
            return result
        except Exception as exc:
            if traceback_mode != 0:
                print(colorama.Style.BRIGHT + colorama.Fore.RED
                      + f'{func.__name__}: {exc}')

    return wrapper


@status
def main():
    get_cache()

    longpoll = init(access_token, group_id)
    listen_events(longpoll)


@status
def init(access_token, group_id):
    global vk_session, longpoll, vk
    vk_session = vk_api.VkApi(token=access_token)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, group_id=group_id)
    return longpoll


@status
def listen_events(longpoll):
    for event in longpoll.listen():

        if event.type == VkBotEventType.MESSAGE_NEW:
            cur_time = convert_to_time(event.obj['date'])
            text = event.obj['text'].strip()
            images = event.obj['attachments']
            if not text and not images:
                continue
            update_statistics(event.obj)
            user = get_user_from_id(event.obj.from_id)
            if text:
                command, *args = text.lower().split()
            if text and command in COMMANDS:
                print(colorama.Fore.BLACK + cur_time
                      + colorama.Back.RESET + '\t'
                      + colorama.Fore.BLUE + colorama.Style.BRIGHT + user
                      + colorama.Back.RESET + '\t'
                      + colorama.Fore.RED + 'Command'
                      + colorama.Back.RESET + '\t'
                      + colorama.Fore.YELLOW + command)
                if COMMANDS[command](*args) is not None:
                    print(colorama.Fore.GREEN + 'Ok')
                else:
                    print(colorama.Fore.RED + 'Failed')
            else:
                if text:
                    print(colorama.Fore.BLACK + cur_time
                          + colorama.Back.RESET + '\t'
                          + colorama.Fore.BLUE + colorama.Style.BRIGHT + user
                          + colorama.Back.RESET + '\t'
                          + colorama.Back.LIGHTBLACK_EX + colorama.Fore.BLACK + 'Message'
                          + colorama.Back.RESET + '\t'
                          + colorama.Fore.YELLOW + text)
                    load_text_to_database(text)
                if images:
                    load_images_to_database(images)


@status
def create_demotivator():
    pass


@status
def load_images_to_database(images):
    for data in images:
        if data['type'] == 'photo':
            name = data['photo']['access_key']
            if name in images_cache:
                return
            url = data['photo']['sizes'][0]['url']
            urllib.request.urlretrieve(url, f"database/images/{name}.jpg")
            images_cache.add(name)


@status
def load_text_to_database(text):
    text = text.strip()
    if text in messages_cache:
        return
    with open('database/messages.txt', 'a') as file:
        file.write(text)
    messages_cache.add(text)


def convert_to_time(date):
    date = int(date)
    s = str(date % 60)
    m = str(date // 60 % 60)
    h = str((date // 3600 + 5) % 24)
    if len(s) == 1:
        s = '0' + s
    if len(m) == 1:
        m = '0' + m
    if len(h) == 1:
        h = '0' + h
    return f'{h}:{m}:{s}'


@status
def get_cache():
    global messages_cache, images_cache
    with open('database/messages.txt', 'r') as file:
        messages_cache = set(file.readlines())

    images_cache = set(os.listdir('database/images'))


def nothing(*args, **kwargs):
    return


@status
def get_statistics():
    with open('info.json', 'r') as file:
        data = json.load(file)
        return data


@status
def update_statistics(message):
    user_id = str(message['from_id'])
    data = get_statistics()
    with open('info.json', 'w') as file:
        if not data.get(user_id, False):
            data[user_id] = {'count': 0, 'name': user_id}
        data[user_id]['count'] += 1
        json.dump(data, file)


@status
def get_user_from_id(id):
    data = get_statistics()
    return str(data[str(id)]['name'])


def terminate():
    os._exit(0)


def wait_for_input():
    try:
        inp = input()
        if send_mode:
            if inp == 'stop':
                switch_send_mode()
            else:
                send(inp)
        else:
            op, *args = inp.split()
            command = TERMINAL_COMMANDS.get(op, nothing)
            command(*args)
    except ValueError:
        pass
    wait_for_input()


def traceback(mode):
    global traceback_mode
    if not mode.isdigit() or not 0 <= int(mode) <= 2:
        return
    traceback_mode = int(mode)
    print(f'Traceback mode switched to {mode}')


@status
def send(text):
    vk_session.method('messages.send', {'random_id': random.getrandbits(32),
                                        'peer_id': 2000000001,
                                        'message': text})


def switch_send_mode():
    global send_mode
    if not send_mode:
        print(colorama.Fore.YELLOW + 'Messaging mode activated')
    else:
        print(colorama.Fore.LIGHTRED_EX + 'Messaging mode deactivated')
    send_mode = not send_mode


COMMANDS = {'bruh': lambda: True}
TERMINAL_COMMANDS = {'send': switch_send_mode, 'exit': terminate, 'traceback': traceback}
if __name__ == '__main__':
    colorama.init(autoreset=True)
    input_thread = threading.Thread(target=wait_for_input)
    input_thread.start()
    main()
    terminate()
