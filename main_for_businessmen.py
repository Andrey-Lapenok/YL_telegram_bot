from telegram import *
from telegram.ext import *
from data.base import *
import asyncio
import datetime
from data.businessmen_data.working_with_data import menu_working_on_inf, registration, get_all_data
from data.businessmen_data.working_with_poll import menu_working_on_poll, get_one_poll, get_one_poll_start
from data.businessmen_data.create_poll import menu_creating_poll, create_poll_select_type, create_poll


def main():
    application = Application.builder().token(TOKEN_FOR_BUSINESSMEN).pool_timeout(10).write_timeout(10). \
        connect_timeout(10).read_timeout(10).get_updates_read_timeout(50).build()
    application.add_handler(CommandHandler("registration", registration))
    application.add_handler(CommandHandler("help", help_bot))
    application.add_handler(CommandHandler("get_tags", send_tags))
    application.add_handler(CommandHandler("get_information_about_yourself", get_all_data))
    application.add_handler(CommandHandler("get_all_polls", get_all_polls))
    application.add_handler(CommandHandler("create_poll", create_poll_select_type))
    application.add_handler(CommandHandler("get_state", get_state_message))
    application.add_handler(CommandHandler("create_tag", create_tag_start))
    application.add_handler(CommandHandler("get_poll", get_one_poll_start))
    application.add_handler(CommandHandler("stop_input_poll_data", menu_working_on_poll.stop_input_data))
    application.add_handler(CommandHandler("stop_input", menu_working_on_inf.stop_input_data))
    application.add_handler(CommandHandler("stop_input_poll_data_creating", menu_creating_poll.stop_input_data))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    application.run_polling()


async def create_tag_start(update, context):
    if not await is_registered(update, context, who=Author):
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    if not check_state({'state': 'waiting'}, author.telegram_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    set_state(author, {'state': 'creating_tag'})
    await update.message.reply_text(text='Введите новый тег\nПример:\n    sport/football/american/football')


async def get_state_message(update, context):
    if not await is_registered(update, context, who=Author):
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    state = ''
    for key in get_state(author):
        state += f'    <b><i>{key}</i></b>: {get_state(author)[key]}\n'

    button = []
    if get_state(author)['state'] != 'waiting':
        button = [[InlineKeyboardButton('End the process', callback_data='end_state')]]

    await update.message.reply_text(text=f'Current state:\n' + state,
                                    parse_mode='HTML', reply_markup=InlineKeyboardMarkup(button))


async def send_tags(update, context):
    if not await is_registered(update, context, who=Author):
        return

    if not check_state({'state': 'waiting'}, update.message.chat_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    bot = Bot(TOKEN_FOR_BUSINESSMEN)
    await bot.send_document(update.message.chat_id, open(file_gen(), 'r'))


async def text(update, context):
    if not await is_registered(update, context, who=Author):
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    state = get_state(author)['state']
    if state == 'working_with_data' or state == 'registration':
        await menu_working_on_inf.text_handler(update, context)

    elif state == 'working_on_poll':
        await menu_working_on_poll.text_handler(update, context)

    elif state == 'creating_poll':
        await menu_creating_poll.text_handler(update, context)

    elif state == 'creating_tag':
        create_tag(update.message.text.strip())
        set_state(author, {'state': 'waiting'})
        await update.message.reply_text(text=f'Новый тег добавлен', parse_mode='HTML')

    elif state == 'getting_poll':
        await get_one_poll(update, context)

    else:
        await update.message.reply_text(text='Бот вас не понимает, воспользуйтесь <i><b>/help</b></i>',
                                        parse_mode='HTML')


async def help_bot(update, context):
    if not await is_registered(update, context, who=Author):
        return
    if not check_state({'state': 'waiting'}, update.message.chat_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    await update.message.reply_text(text='<i><b>/registration</b></i> - регистрация\n'
                                         '<i><b>/get_information_about_yourself</b></i> - получить информацию о себе\n'
                                         '<i><b>/create_poll</b></i> - создать опрос\n'
                                         '<i><b>/get_all_polls</b></i> - получить названия всех ваших опросов\n'
                                         '<i><b>/get_poll</b></i> - получить всю информацию об опросе\n'
                                         '<i><b>/get_tags</b></i> - получить все теги\n'
                                         '<i><b>/create_tag</b></i> - создать тег\n'
                                         '<i><b>/get_state</b></i> - получить текущее состояние', parse_mode='HTML')


async def callback_handler(update, context):
    query = update.callback_query
    author = db_sess.query(Author).filter(Author.telegram_id == update.callback_query.message.chat_id).first()
    _type = get_data_from_button(query)['type']

    if query.data == 'end_state':
        set_state(author, {'state': 'waiting'})
        await query.edit_message_text(text=f'Current state:\n    <i><b>state</b></i>: waiting', parse_mode='HTML')

    elif _type == 'work_data':
        await menu_working_on_inf.callback_handler(update, context)

    elif _type == 'work_poll':
        await menu_working_on_poll.callback_handler(update, context)

    elif _type == 'create_poll':
        if get_data_from_button(query)['data'][2] == '1' or get_data_from_button(query)['data'][2] == '2':
            await menu_creating_poll.callback_handler(update, context)

    elif _type == 'sel_type':
        await create_poll(update, context)


async def get_all_polls(update, context):
    if not await is_registered(update, context, who=Author):
        return

    if not check_state({'state': 'waiting'}, update.message.chat_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    polls_type_1 = db_sess.query(Poll1).filter(Poll1.author == author.id).all()
    polls_type_2 = db_sess.query(Poll2).filter(Poll2.author == author.id).all()
    text_of_mes = 'Все ваши опросы:\n'
    if len(polls_type_1 + polls_type_2) == 0:
        await update.message.reply_text(text='У вас ни одного опроса')
        return

    if len(polls_type_1) != 0:
        text_of_mes += '    Опросы первого типа:\n'
        for index, question in enumerate(polls_type_1):
            text_of_mes += f'        {index + 1}. {question.title} (id: {question.id},' \
                           f' {"active" if question.is_active else "not active"})\n'
    if len(polls_type_2) != 0:
        text_of_mes += '    Опросы второго типа:\n'
        for index, question in enumerate(polls_type_2):
            text_of_mes += f'        {index + 1}. {question.title} (id: {question.id},' \
                           f' {"active" if question.is_active else "not active"})\n'

    await update.message.reply_text(text=text_of_mes)


if __name__ == '__main__':
    main()
