from telegram import *
from telegram.ext import *
from data.base import *
import asyncio
import sqlite3
from data.user_data.polls_type_1 import *
from data.user_data.polls_type_2 import *


async def send_poll(telegram_id, ordinarily=True):
    bot = Bot(TOKEN)
    user = db_sess.query(OurUser).filter(OurUser.telegram_id == telegram_id).first()

    if not user and not ordinarily:
        await bot.send_message(telegram_id, 'К сожалению, мы не можем дать вам опрос, так как вы не зарегистрированы')
        return

    questions = []
    for question in db_sess.query(Poll1).filter(Poll1.is_active).all():
        if question.id not in get_received_polls_of_user(user, 1) and question.balance >= question.check_per_person:
            questions.append([question, check_tag_match(user, question)])
        elif question.balance < question.check_per_person:
            question.is_active = False
            db_sess.commit()
    for question in db_sess.query(Poll2).filter(Poll2.is_active).all():
        if question.id not in get_received_polls_of_user(user, 2) and question.balance >= question.check_per_person:
            questions.append([question, check_tag_match(user, question)])
        elif question.balance < question.check_per_person:
            question.is_active = False
            db_sess.commit()

    if not questions:
        if not ordinarily:
            await bot.send_message(telegram_id, 'К сожалению, у нас нет опросов для вас')
        return None

    poll = max(questions, key=lambda x: x[1])[0]
    append_received_poll(user, poll, '1' if type(poll) == Poll1 else '2')
    poll.balance -= poll.check_per_person
    db_sess.commit()
    reply_markup = None
    if type(poll) == Poll1:
        reply_markup = get_reply_markup_type_1(poll, user, 'get_information')

    await bot.send_message(telegram_id, poll.text_of_question, reply_markup=reply_markup)


async def send_poll_by_request(update, context):
    if not await is_registered(update, context):
        return

    if not check_state({'state': 'waiting'}, update.message.chat_id)\
            and not check_state({'state': 'ready'}, update.message.chat_id):
        await update.send_message(text='Вы не можете начать новое действие, не закончив старое')
        return

    await asyncio.create_task(send_question(update.message.chat_id, ordinarily=False))


async def callback_polls(query, user):
    type_of_data = get_data_from_button(query)['data'][0]

    if type_of_data == 'answer':
        await callback_1(query)

    elif type_of_data == 'information':
        await append_information(query, user)

    elif type_of_data == 'd_information':
        await delete_information(query, user)


async def append_information(query, user):
    poll_type = Poll1 if get_data_from_button(query)['type'] == 'type_1' else Poll2
    question_id = get_data_from_button(query)['data'][1]
    question = db_sess.query(poll_type).filter(poll_type.id == question_id).first()
    author = db_sess.query(Author).filter(Author.id == question.author).first()
    border_date = question.border_date.strftime("%d %B, %Y")
    text_answer = ''
    reply_markup = None
    if poll_type == Poll1:
        text_answer = get_text_type_1(question, user)
        reply_markup = get_reply_markup_type_1(question, user, 'delete_information')
    await query.edit_message_text(text=f'{question.text_of_question}\n' + text_answer +
                                       f'\n\n<b><i>Additional information:</i></b>\n'
                                       f'<b><i>Автор:</i></b> {author.name}\n'
                                       f'<b><i>Информация об авторе:</i></b> {author.additional_information}\n'
                                       f'<b><i>Контакты автора:</i></b> {author.email}\n'
                                       f'<b><i>Активен до:</i></b> {border_date}\n'
                                       f'<b><i>Описание:</i></b> {question.additional_information}\n'
                                       f'<b><i>Вам будет перечислено:</i></b> {question.check_per_person} рублей',
                                  parse_mode='HTML', reply_markup=reply_markup)


async def delete_information(query, user):
    poll_type = Poll1 if get_data_from_button(query)['type'] == 'type_1' else Poll2
    question_id = get_data_from_button(query)['data'][1]
    question = db_sess.query(poll_type).filter(poll_type.id == question_id).first()
    text_answer = ''
    reply_markup = None
    if poll_type == Poll1:
        text_answer = get_text_type_1(question, user)
        reply_markup = get_reply_markup_type_1(question, user, 'get_information')
    await query.edit_message_text(text=f'{question.text_of_question}\n' + text_answer,
                                  parse_mode='HTML', reply_markup=reply_markup)
