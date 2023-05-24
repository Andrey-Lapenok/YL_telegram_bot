import datetime
from telegram import *
from telegram.ext import *
from orm_support.db_connect import *
from orm_support.all_db_models import *
from data.base import *
import asyncio
import csv
import sqlite3


def get_reply_markup(question, user, type):
    answers = get_answers_as_list(question)
    buttons = []
    if question.id not in get_answers_of_user(user):
        if len(answers) > 2:
            buttons = [
                [InlineKeyboardButton(answer['answer'], callback_data=f'answer_1|{question.id}|{answers.index(answer)}')]
                for answer in answers]
        else:
            buttons = [
                [InlineKeyboardButton(answer['answer'], callback_data=f'answer_1|{question.id}|{answers.index(answer)}')
                 for answer in answers]]

    if type == 'get_information':
        buttons.append([InlineKeyboardButton('ℹ️informationℹ', callback_data=f'information|{question.id}')])

    elif type == 'delete_information':
        buttons.append([InlineKeyboardButton('ℹ️delete informationℹ', callback_data=f'd_information|{question.id}')])
    return InlineKeyboardMarkup(buttons)


def set_answer_1(question, answer):
    answers = get_answers_as_dict(question)
    answers[answer] += 1
    question.answers = '|'.join(list(map(lambda x: f'{x}:{answers[x]}', answers)))
    db_sess.commit()


async def send_question_1(telegram_id, ordinarily=True):
    bot = Bot(TOKEN)
    user = db_sess.query(OurUser).filter(OurUser.telegram_id == telegram_id).first()

    if not user and not ordinarily:
        await bot.send_message(telegram_id, 'К сожалению, мы не можем дать вам опрос, так как вы не зарегистрированы')
        return

    questions = []
    for question in db_sess.query(Question).filter(Question.is_active).all():
        if (user.polls_received is not None and str(question.id) not in user.polls_received.split(',')) or (
                user.polls_received is None and get_vote_as_dict(question.id, user) is None)\
                and question.balance >= question.check_per_person:
            questions.append([question.id, check_tag_match(user, question)])
        elif question.balance < question.check_per_person:
            question.is_active = False
            db_sess.commit()

    if not questions:
        if not ordinarily:
            await bot.send_message(telegram_id, 'К сожалению, у нас нет опросов для вас')
        return None

    question = db_sess.query(Question).filter(Question.id == max(questions, key=lambda x: x[1])[0]).first()
    append_received_poll(user, question)
    question.balance -= question.check_per_person
    db_sess.commit()

    await bot.send_message(telegram_id, question.text_of_question, reply_markup=get_reply_markup(
        question, user, type='get_information'))


async def send_question_1_by_request(update, context):
    if not await is_registered(update, context):
        return

    if not check_state({'state': 'waiting'}, update.message.chat_id)\
            and not check_state({'state': 'ready'}, update.message.chat_id):
        await update.send_message(text='Вы не можете начать новое действие, не закончив старое')
        return
    await asyncio.create_task(send_question_1(update.message.chat_id, ordinarily=False))


async def callback_1(query):
    question_id, number_of_answer = query.data.split('|')[1:]
    number_of_answer = int(number_of_answer)
    question = db_sess.query(Question).filter(Question.id == question_id).first()
    user = db_sess.query(OurUser).filter(OurUser.telegram_id == query.message.chat_id).first()
    append_answered_poll(user, question)
    user.balance += question.check_per_person
    db_sess.commit()

    answer = get_answers_as_list(question)[number_of_answer]['answer']
    set_answer_1(question, answer)

    con = sqlite3.connect('db/Results.db')
    cur = con.cursor()
    cur.execute(f"""INSERT INTO Poll_{question.id}(user_id, answer_index, answer_text, date, tags)
                VALUES(?, ?, ?, ?, ?);""", (user.id, number_of_answer, answer,
                                            datetime.datetime.now().strftime('%Y-%m-%d'), user.tags))
    con.commit()
    con.close()

    text_of_message = query.message.text.split('\n\nAdditional information:\n')[0]
    await query.edit_message_text(text=f"{text_of_message}\nВы выбрали: <i><b>{answer}</b></i>",
                                  parse_mode='HTML', reply_markup=get_reply_markup(question, user,
                                                                                   type='get_information'))
