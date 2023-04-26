import logging
from telegram import *
from telegram.ext import *
from orm_support.db_connect import *
from orm_support.all_db_models import *
from data.user_data.question_1 import *
from re import findall
from data.user_data.working_with_information import *
from data.base import *
import asyncio
from functools import partial
import datetime
import csv


def main():
    make_log('debug', 'main', 'Start main')
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("registration", registrate))
    application.add_handler(CommandHandler("get", send_question_1_by_request))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("delete_data", delete_data))
    application.add_handler(CommandHandler("get_tags", send_tags))
    application.add_handler(CommandHandler("get_information_about_yourself", get_all_data))
    application.add_handler(CommandHandler("get_state", get_state_message))
    application.add_handler(CommandHandler("create_tag", create_tag_start))
    application.add_handler(CommandHandler("stop_input", stop_work_with_inf))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    loop = asyncio.get_event_loop()
    loop.create_task(running())
    loop.create_task((check_questions_date()))
    application.run_polling()


async def running():
    while True:
        make_log('debug', 'main', 'Start wait before update users')
        await asyncio.sleep(10)
        make_log('debug', 'main', 'Start update users')
        users = db_sess.query(OurUser).all()
        for user in users:
            update_user(user)
        make_log('debug', 'main', 'Complete update users')


async def check_questions_date():
    delay = 60 * 60 * 24
    while True:
        make_log('debug', 'main', 'Start waiting before checking border date')
        await asyncio.sleep(delay)
        make_log('debug', 'main', 'Complete waiting before checking border date')
        questions = db_sess.query(Question).all()
        for question in questions:
            if question.is_active and question.border_date < datetime.datetime.now():
                question.is_active = False
                db_sess.commit()

            elif not question.is_active and question.border_date > datetime.datetime.now():
                question.border_date += datetime.timedelta(seconds=delay)
        make_log('debug', 'main', 'Complete checking border date')


def update_user(user):
    if get_state(user)['state'] == 'waiting' and user.next_poll_time <= datetime.datetime.now():
        set_state(user, {'state': 'ready'})
        user.next_poll_time = datetime.datetime.now() + datetime.timedelta(minutes=user.waiting_time)
        db_sess.commit()

    if get_state(user)['state'] == 'ready':
        set_state(user, {'state': 'waiting'})
        db_sess.commit()
        asyncio.create_task(send_question_1(user.telegram_id))


async def get_state_message(update, context):
    if not await is_registered(update, context):
        return

    user = db_sess.query(OurUser).filter(OurUser.telegram_id == update.message.chat_id).first()
    state = ''
    for key in get_state(user):
        state += f'    <b><i>{key}</i></b>: {get_state(user)[key]}\n'

    button = []
    if get_state(user)['state'] != 'waiting':
        button = [[InlineKeyboardButton('End the process', callback_data='end_state')]]

    await update.message.reply_text(text=f'Current state:\n' + state,
                                    parse_mode='HTML', reply_markup=InlineKeyboardMarkup(button))


async def text(update, context):
    make_log('debug', 'main', 'Received text message')
    if not await is_registered(update, context):
        make_log('debug', 'main', 'Text processing not started')
        return

    user = db_sess.query(OurUser).filter(OurUser.telegram_id == update.message.chat_id).first()
    state = get_state(user)['state']
    if state == 'working_with_data' or state == 'registration':
        asyncio.create_task(text_handler_working_with_data(update, context))

    elif state == 'create_tag':
        create_tag(update.message.text.strip())
        set_state(user, {'state': 'waiting'})
        await update.message.reply_text(text=f'Новый тег добавлен', parse_mode='HTML')

    else:
        make_log('debug', 'main', 'Empty message, start send message')
        await update.message.reply_text(text='Бот вас не понимает, воспользуйтесь <i><b>/help</b></i>',
                                        parse_mode='HTML')
    make_log('debug', 'main', 'Complete text_handler working')


async def help(update, context):
    if not await is_registered(update, context):
        return
    if not check_state({'state': 'waiting'}, update.message.chat_id):
        await update.message.reply_text(text=f'Вы не можете начать новое дейтсвие, не закончив старое')
        return
    await update.message.reply_text(text='<i><b>/get</b></i> - получения опроса\n'
                                         '<i><b>/registration</b></i> - регистрация\n'
                                         '<i><b>/delete_data</b></i> - удаление о себе всей информации с серверов\n'
                                         '<i><b>/get_information_about_yourself</b></i>'
                                         ' - получить всю информацию о вас\n'
                                         '<i><b>/get_tags</b></i> - получение тегов\n'
                                         '<i><b>/create_tag</b></i> - создать новый тег\n'
                                         '<i><b>/get_state</b></i> - получить текущее состояние',
                                    parse_mode='HTML')


async def send_tags(update, context):
    if not await is_registered(update, context):
        return
    if not check_state({'state': 'waiting'}, update.message.chat_id):
        await update.message.reply_text(text=f'Вы не можете начать новое дейтсвие, не закончив старое')
        return

    bot = Bot(TOKEN)
    await bot.send_document(update.message.chat_id, open(file_gen(), 'r'))


async def delete_data(update, context):
    if not await is_registered(update, context):
        return

    if not check_state({'state': 'waiting'}, update.message.chat_id):
        await update.message.reply_text(text=f'Вы не можете начать новое дейтсвие, не закончив старое')
        return

    user = db_sess.query(OurUser).filter(OurUser.telegram_id == update.message.chat_id).first()
    if not check_state({'state': 'waiting'}, user.telegram_id):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    db_sess.query(OurUser).filter(OurUser.telegram_id == update.message.chat_id).delete()
    db_sess.commit()
    await update.message.reply_text(text='Ваши данные полностью удалены, теперь вам будут'
                                         ' недоступны функции бота. Если хотите вернуться,'
                                         ' воспользуйтесь <i><b>/registration</b></i>', parse_mode='HTML')


async def create_tag_start(update, context):
    if not await is_registered(update, context, who=OurUser):
        return

    user = db_sess.query(OurUser).filter(OurUser.telegram_id == update.message.chat_id).first()
    if not check_state({'state': 'waiting'}, user.telegram_id, who=OurUser):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    set_state(user, {'state': 'create_tag'})
    await update.message.reply_text(text='Введите новый тег\nПример:\n    sport/football/american/football')


async def unknown_command(update, context):
    if not await is_registered(update, context):
        return

    if not check_state({'state': 'waiting'}, update.message.chat_id):
        await update.message.reply_text(text=f'Вы не можете начать новое дейтсвие, не закончив старое')
        return

    if findall(r'/stop_registration', update.message.text) and not findall(r'/stop_registration.+',
                                                                           update.message.text):
        await update.message.reply_text(text='Данную команду можно использовать только в течение регистрации',
                                        parse_mode='HTML')
        return
    await update.message.reply_text(text='Бот не предусматривает такой команды, воспользутесь <i><b>/help</b></i>',
                                    parse_mode='HTML')


async def callback_handler(update, context):
    query = update.callback_query
    user = db_sess.query(OurUser).filter(OurUser.telegram_id == query.message.chat_id).first()
    type_of_data = get_data_from_button(query)['type']

    if type_of_data == 'end_state':
        try:
            await asyncio.create_task(delete_messages(user))
        finally:
            set_state(user, {'state': 'waiting'})
        await query.edit_message_text(text=f'Current state:\n    <i><b>state</b></i>: waiting', parse_mode='HTML')

    if not await is_registered(update, context, is_called_from_query=True):
        await query.edit_message_text(text='Вы не зарегистриованы, воспользуйтесь <i><b>/registration</b></i>',
                                      parse_mode='HTML')

    if type_of_data == 'work_inf':
        await callback_handler_working_with_data(update, context)

    elif type_of_data == 'answer_1':
        await callback_1(query)

    elif type_of_data == 'information':
        question_id = query.data.split('|')[1]
        question = db_sess.query(Question).filter(Question.id == question_id).first()
        author = db_sess.query(Author).filter(Author.id == question.author).first()
        border_date = question.border_date.strftime("%d %B, %Y")
        answer = get_vote_as_dict(question_id, user)
        text_answer = ''
        if answer is not None:
            text_answer = f'Вы выбрали: <b><i>{answer["answer_text"]}</i></b>'
        await query.edit_message_text(text=f'{question.text_of_question}\n' + text_answer +
                                           f'\n\n<b><i>Additional information:</i></b>\n'
                                           f'<b><i>Автор:</i></b> {author.name}\n'
                                           f'<b><i>Информация об авторе:</i></b> {author.additional_information}\n'
                                           f'<b><i>Контакты автора:</i></b> {author.email}\n'
                                           f'<b><i>Активен до:</i></b> {border_date}\n'
                                           f'<b><i>Описание:</i></b> {question.additional_information}\n'
                                           f'<b><i>Вам будет перечислено:</i></b> {question.check_per_person} рублей',
                                      parse_mode='HTML',
                                      reply_markup=get_reply_markup(question, user, type='delete_information'))

    elif type_of_data == 'd_information':
        question_id = query.data.split('|')[1]
        question = db_sess.query(Question).filter(Question.id == question_id).first()
        answer = get_vote_as_dict(question_id, user)
        text_answer = ''
        if answer is not None:
            text_answer = f'Вы выбрали: <b><i>{answer["answer_text"]}</i></b>'
        await query.edit_message_text(text=f'{question.text_of_question}\n' + text_answer,
                                      parse_mode='HTML',
                                      reply_markup=get_reply_markup(question, user, type='get_information'))

if __name__ == '__main__':
    main()
