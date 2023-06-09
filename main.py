from telegram import *
from telegram.ext import *
from data.user_data.polls_distributor import *
from re import findall
from data.base import *
import asyncio
import datetime
from data.user_data.working_with_inf import menu_working_on_inf, registrate, get_all_data


def main():
    make_log('debug', 'main', 'Start main')
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("registration", registrate))
    application.add_handler(CommandHandler("get", send_poll_by_request))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("delete_data", delete_data))
    application.add_handler(CommandHandler("get_tags", send_tags))
    application.add_handler(CommandHandler("get_information_about_yourself", get_all_data))
    application.add_handler(CommandHandler("get_state", get_state_message))
    application.add_handler(CommandHandler("create_tag", create_tag_start))
    application.add_handler(CommandHandler("stop_input", menu_working_on_inf.stop_input_data))
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
        questions = db_sess.query(Poll1).all()
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
        asyncio.create_task(send_poll(user.telegram_id))


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
        await menu_working_on_inf.text_handler(update, context)

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
        await menu_working_on_inf.callback_handler(update, context)

    elif type_of_data in ['type_1', 'type_2']:
        await callback_polls(query, user)


if __name__ == '__main__':
    main()
