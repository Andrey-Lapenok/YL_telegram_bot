from orm_support.db_connect import *
from orm_support.all_db_models import *
from telegram import *
from telegram.ext import *
from yookassa import Configuration, Payment, Payout
import csv
import logging
import json
import uuid
import sqlite3


TOKEN = '6067604242:AAEMX9qetuikGF5TexuKXPxJfjlWn6O5rsI'
TOKEN_FOR_BUSINESSMEN = '6231661577:AAH5hiR76UBnGisYORjTrHh1egIyCh4E5wo'
PAYMENT_TOKEN = 'test_9WDqIF3DFMvU_0qpgeNrc_LipQgzbz8-N0kz_dajAwA'
SHOP_ID = '314953'
global_init("db/DB.db")
db_sess = create_session()
# logging.basicConfig(filename='another logging.log', format='%(asctime)s || %(levelname)s || %(message)s',
#                     level=logging.DEBUG)
# logging.basicConfig(format='%(asctime)s: %(levelname)s: %(name)s %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_handler = logging.FileHandler(f"logging.log", mode='w')
log_handler.setFormatter(logging.Formatter("%(asctime)s || %(levelname)s || %(message)s"))
logger.addHandler(log_handler)
header_of_vote_files = ['user_id', 'answer_index', 'answer_text', 'date', 'tags']


def create_invoice(chat_id, amount, person, message_id):
    Configuration.account_id = SHOP_ID
    Configuration.secret_key = PAYMENT_TOKEN

    payment = Payment.create({
        "amount": {
            "value": f"{amount}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://www.google.com"
        },
        "capture": True,
        "description": "Заказ №1",
        "metadata": {"chat_id": chat_id, "user": True if person == "user" else False,
                     "author": True if person == "author" else False,
                     "message": message_id}
    })

    return payment.confirmation.confirmation_url


def create_payout():
    Configuration.account_id = SHOP_ID
    Configuration.secret_key = PAYMENT_TOKEN
    idempotence_key = str(uuid.uuid4())
    res = Payout.create({
        "amount": {"value": 320.0, "currency": "RUB"},
        "payout_destination_data": {'type': "yoo_money", 'account_number': '41001614575714'},
        "description": "Выплата по заказу №37",
        "metadata": {
            "order_id": "37"
        },
        "deal": {
            "id": "dl-285e5ee7-0022-5000-8000-01516a44b147"
        }
    })
    print(res)
    return 'er'


def make_log(level, name, msg):
    levels = {'debug': logger.debug, 'info': logger.info, 'warning': logger.warning, 'error': logger.error}
    if level in levels:
        levels[level](name + ' || ' + msg)
    else:
        make_log('error', 'base', f'Not exist level {level}')


async def is_registered(update, context, is_called_from_query=False, who=OurUser):
    make_log('debug', 'base', 'Start check registration')
    if is_called_from_query:
        db_entry = db_sess.query(who).filter(who.telegram_id == update.callback_query.message.chat_id).first()
    else:
        db_entry = db_sess.query(who).filter(who.telegram_id == update.message.chat_id).first()

    if db_entry:
        make_log('debug', 'base', 'Complete check registration, return true')
        return True
    elif not is_called_from_query:
        make_log('debug', 'base', 'Check registration, send message')
        await update.message.reply_text(text='Вы не зарегистрированы, воспользуйтесь <i><b>/registration</b></i>',
                                        parse_mode='HTML')
        make_log('debug', 'base', 'Complete check registration, return false')
        return False


def check_state(needed_state, telegram_id, who=OurUser):
    person = db_sess.query(who).filter(who.telegram_id == telegram_id).first()
    person_state = get_state(person)

    if person_state['state'] != needed_state['state']:
        return False

    for name in needed_state:
        if person_state[name] != needed_state[name]:
            break

    else:
        return True

    return False


def get_answers_as_list(question):
    return list(map(lambda x: {'answer': x.split(':')[0],
                               'numbers': int(x.split(':')[1])}, question.answers.split('|')))


def get_answers_as_dict(question):
    answers = {}
    for answer in question.answers.split('|'):
        answers[answer.split(':')[0]] = int(answer.split(':')[1])

    return answers


def set_state(person, current_state):
    # person.current_state = '|'.join(list(map(lambda x: f'{x}:{current_state[x]}', current_state)))
    person.current_state = json.dumps(current_state)
    db_sess.commit()


def change_state_characteristic(author, characteristic, value):
    current_state = get_state(author)
    if characteristic not in current_state:
        current_state[characteristic] = None
    current_state[characteristic] = value
    set_state(author, current_state)
    db_sess.commit()


def get_state(person):
    # current_state = {}
    # for characteristic in a.current_state.split('|'):
    #     current_state[characteristic.split(':')[0]] = characteristic.split(':')[1]
    return json.loads(person.current_state)


def get_answers_of_user(user):
    if user.answered_polls:
        return list(map(int, filter(lambda x: x != '', user.answered_polls.split(','))))

    return []


def file_gen():
    path = "db/tags.txt"
    with open(path, 'w') as file:
        file.write(get_tags_recursion(json.load(open('db/tags.json', 'r')), 0))
    return path


def get_tags_recursion(objects, level):
    if objects == {}:
        return ''

    else:
        a = ''
        for obj in objects:
            a += '\t' * level + obj + '\n' + get_tags_recursion(objects[obj], level + 1)
        return a


def create_tag(path):
    path = path.split('/')
    with open('db/tags.json', 'r') as file:
        tags = json.load(file)
        current_level = tags

    for level in path:
        if level not in current_level:
            current_level[level] = {}

        current_level = current_level[level]

    with open('db/tags.json', 'w') as file:
        json.dump(tags, file)


def sort_tags(_tags):
    all_invalid_tags = []

    with open(file_gen(), 'r') as file:
        all_existing_tags = list(map(lambda x: x.strip(), file.readlines()))

        for tag in _tags.split(','):
            if tag not in all_existing_tags:
                all_invalid_tags.append(tag)

        all_correct_tags = list(set(filter(lambda x: x not in all_invalid_tags, _tags.split(','))))
    all_invalid_tags = list(set(all_invalid_tags))
    return {"correct_tags": all_correct_tags, "invalid_tags": all_invalid_tags}


def check_tag_match(user, question):
    if question.needed_tags is None or user.tags is None:
        return 0

    tags_if_question = question.needed_tags.split(',')
    return sum(list(map(lambda x: 1 if x in tags_if_question else -1, user.tags.split(','))))


def get_vote_as_dict(question_id, user):
    con = sqlite3.connect('db/Results_type_1.db')
    cur = con.cursor()
    answer = cur.execute(f"""SELECT * FROM Poll_{question_id} WHERE user_id = {user.id}""").fetchone()
    con.close()
    if answer is None:
        return None
    return {header_of_vote_files[i]: answer[i] for i in range(len(header_of_vote_files))}


def get_all_votes_with_tags(question_id, needed_tags):
    con = sqlite3.connect('db/Results_type_1.db')
    cur = con.cursor()
    votes = [{header_of_vote_files[i]: vote[i] for i in range(len(header_of_vote_files))}
             for vote in cur.execute(f"""SELECT * FROM Poll_{question_id}""").fetchall()]
    all_votes = []

    for vote in votes:
        if vote['tags'] is not None and set(needed_tags).issubset(set(vote['tags'].split(','))):
            all_votes.append(vote)

    return all_votes


def append_mes_to_delete(person, message):
    if 'mes_to_delete' not in get_state(person):
        change_state_characteristic(person, 'mes_to_delete', [])

    if get_state(person)['mes_to_delete']:
        mes_to_delete = get_state(person)['mes_to_delete']

        if type(message) == int:
            change_state_characteristic(person, 'mes_to_delete', list(set(mes_to_delete + [message])))
        else:
            change_state_characteristic(person, 'mes_to_delete', list(set(mes_to_delete + [message.message_id])))

    else:
        if type(message) == int:
            change_state_characteristic(person, 'mes_to_delete', [message])
        else:
            change_state_characteristic(person, 'mes_to_delete', [message.message_id])


async def delete_messages(person):
    if 'mes_to_delete' not in get_state(person):
        return

    bot = Bot(TOKEN)
    if type(person) == Author:
        bot = Bot(TOKEN_FOR_BUSINESSMEN)

    if get_state(person)['mes_to_delete']:
        for mes_id in get_state(person)['mes_to_delete']:
            await bot.delete_message(person.telegram_id, mes_id)

        change_state_characteristic(person, 'mes_to_delete', [])


def append_received_poll(user, question):
    if user.polls_received:
        user.polls_received = ','.join(list(filter(lambda x: x != '', user.polls_received.
                                                   replace(' ', '').split(',') + [str(question.id)])))
    else:
        user.polls_received = f'{question.id}'


def append_answered_poll(user, question):
    if user.answered_polls:
        user.answered_polls = ', '.join(list(filter(lambda x: x != '', user.answered_polls.
                                                    replace(' ', '').split(',') + [str(question.id)])))
    else:
        user.answered_polls = f'{question.id}'


def get_data_from_button(query):
    return {'type': query.data.split('|')[0], 'data': query.data.split('|')[1:]}
