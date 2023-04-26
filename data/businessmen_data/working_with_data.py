import asyncio
from telegram import *
from telegram.ext import *
from orm_support.all_db_models import *
from data.base import *
from data.change_handlers import *
import datetime


async def get_all_data(update, context):
    if not await is_registered(update, context, who=Author):
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    if not check_state({'state': 'waiting'}, author.telegram_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    set_state(author, {'state': 'working_with_data', 'current_state': 'None', 'mes_to_delete': ''})
    await update.message.reply_text(text=get_text_of_data(author),
                                    parse_mode='HTML', reply_markup=get_buttons(author))


async def registration(update, context):
    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    if author:
        await update.message.reply_text(text=' Вы уже зарегистрированы, воспользуйтесь <i><b>/help</b></i>,'
                                             ' чтобы увидеть все возможности', parse_mode='HTML')
        return

    author = Author()
    author.telegram_id = update.message.chat_id
    db_sess.add(author)
    db_sess.commit()
    set_state(author, {'state': 'registration', 'current_state': 'None', 'mes_to_delete': ''})
    await update.message.reply_text(text=get_text_of_data(author),
                                    parse_mode='HTML', reply_markup=get_buttons(author))


async def callback_handler_working_with_data(update, context):
    query = update.callback_query
    data = get_data_from_button(query)['data'][0]
    author = db_sess.query(Author).filter(Author.telegram_id == query.message.chat_id).first()
    await asyncio.create_task(delete_messages(author))
    if not check_state({'state': 'working_with_data'}, author.telegram_id, who=Author) and not\
            check_state({'state': 'registration'}, author.telegram_id, who=Author):
        await query.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        await query.edit_message_text(text=get_text_of_data(author), parse_mode='HTML')
        return

    if data == 'stop':
        if author.name and author.additional_information and author.email:
            await query.edit_message_text(text=get_text_of_data(author), parse_mode='HTML')
            set_state(author, {'state': 'waiting'})
            return
        else:
            await context.bot.answer_callback_query(callback_query_id=query.id,
                                                    text='Нельзя завершить процесс, так как не все поля заполнены',
                                                    show_alert=True)
            return

    markup = ReplyKeyboardMarkup([['/stop_input_data']], one_time_keyboard=False)
    mes = await query.message.reply_text(
        text="Нажмите на кнопку <b><i>/stop_input_data</i></b>, если хотите прекратить ввод",
        parse_mode='HTML', reply_markup=markup)
    append_mes_to_delete(author, mes)

    all_functions = {'ch_name': callback_change_name, 'ch_inf': callback_change_additional_information,
                     'ch_email': callback_change_email}
    mes = await all_functions[data](query, author)

    append_mes_to_delete(author, query.message)
    append_mes_to_delete(author, mes)

    await query.edit_message_text(text=get_text_of_data(author), parse_mode='HTML')


def get_buttons(author):
    buttons = [[InlineKeyboardButton('Change name', callback_data=f'work_data|ch_name'),
                InlineKeyboardButton('Change email', callback_data=f'work_data|ch_email')],
               [InlineKeyboardButton('Change additional information', callback_data=f'work_data|ch_inf')]]
    
    if get_state(author)['state'] == 'registration':
        buttons.append([InlineKeyboardButton('Accept', callback_data='work_data|stop')])
    else:
        buttons.append([InlineKeyboardButton('Stop', callback_data='work_data|stop')])

    return InlineKeyboardMarkup(buttons)


def get_text_of_data(author):
    return f'<i><b>Name:</b></i> {author.name}\n'\
           f'<i><b>Additional information:</b></i> {author.additional_information}\n'\
           f'<i><b>Email:</b></i> {author.email}\n' \
           f'<i><b>Balance:</b></i> {author.balance} rubles'


async def text_handler_working_with_data(update, context):
    all_functions = {'changing_name': change_name, 'changing_additional_information': change_additional_information,
                     'changing_email': change_email, 'None': invalid_text}
    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()

    append_mes_to_delete(author, update.message)
    await asyncio.create_task(delete_messages(author))

    current_state = get_state(author)['current_state']
    mes = await all_functions[current_state](update, author)
    append_mes_to_delete(author, mes)

    change_state_characteristic(author, 'current_state', 'None')
    await update.message.reply_text(text=get_text_of_data(author),
                                    parse_mode='HTML', reply_markup=get_buttons(author))


async def stop_input_data(update, context):
    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    append_mes_to_delete(author, update.message)
    await delete_messages(author)
    change_state_characteristic(author, 'current_state', 'None')
    mes = await update.message.reply_text(text='Ввод прекращен')
    append_mes_to_delete(author, mes)
    await update.message.reply_text(text=get_text_of_data(author),
                                    parse_mode='HTML', reply_markup=get_buttons(author))
