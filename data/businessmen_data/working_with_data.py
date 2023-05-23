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
    mes = await update.message.reply_text(text=get_text_of_data(author),
                                          parse_mode='HTML', reply_markup=get_buttons(author))
    change_state_characteristic(author, 'menu', mes.message_id)


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
    mes = await update.message.reply_text(text=get_text_of_data(author),
                                          parse_mode='HTML', reply_markup=get_buttons(author))
    change_state_characteristic(author, 'menu', mes.message_id)


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
    bot = Bot(TOKEN_FOR_BUSINESSMEN)
    if data == 'test':
        await bot.answer_callback_query(callback_query_id=query.message.message_id,
                                        text='Нельзя завершить процесс, так как не все поля заполнены',
                                        show_alert=True, cache_time=10)
        return
    all_functions = {'ch_name': callback_change_name, 'ch_inf': callback_change_additional_information,
                     'ch_email': callback_change_email, 'rep_bal': callback_replenish_balance,
                     'stop': stop_working_with_data, 'update': callback_working_with_data_update}
    mode, data = await all_functions[data](query, author)

    if mode == 'ordinary':
        markup = ReplyKeyboardMarkup([['/stop_input_data']], one_time_keyboard=False)
        mes = await query.message.reply_text(
            text="Нажмите на кнопку <b><i>/stop_input_data</i></b>, если хотите прекратить ввод",
            parse_mode='HTML', reply_markup=markup)
        append_mes_to_delete(author, mes)
        if type(data['message']) == list:
            for message in data['message']:
                append_mes_to_delete(author, message)
        else:
            append_mes_to_delete(author, data['message'])
        await query.edit_message_text(text=get_text_of_data(author), parse_mode='HTML')
    elif mode == 'stopping':
        return


def get_buttons(author):
    buttons = [[InlineKeyboardButton('Change name', callback_data=f'work_data|ch_name'),
                InlineKeyboardButton('Change email', callback_data=f'work_data|ch_email')],
               [InlineKeyboardButton('Change additional information', callback_data=f'work_data|ch_inf')],
               [InlineKeyboardButton('Replenish balance', callback_data=f'work_data|rep_bal')]]
    
    if get_state(author)['state'] == 'registration':
        buttons.append([InlineKeyboardButton('Accept', callback_data='work_data|stop')])
    else:
        buttons.append([InlineKeyboardButton('Stop', callback_data='work_data|stop')])

    buttons.append([InlineKeyboardButton('Update', callback_data='work_data|update')])
    buttons.append([InlineKeyboardButton('Test', callback_data='work_data|test')])

    return InlineKeyboardMarkup(buttons)


def get_text_of_data(author):
    return f'<i><b>Name:</b></i> {author.name}\n'\
           f'<i><b>Additional information:</b></i> {author.additional_information}\n'\
           f'<i><b>Email:</b></i> {author.email}\n' \
           f'<i><b>Balance:</b></i> {author.balance} rubles'


async def text_handler_working_with_data(update, context):
    all_functions = {'changing_name': change_name, 'changing_additional_information': change_additional_information,
                     'changing_email': change_email, 'replenishing_balance': replenish_balance, 'None': invalid_text}
    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()

    append_mes_to_delete(author, update.message)
    await delete_messages(author)

    current_state = get_state(author)['current_state']
    mode, data = await all_functions[current_state](update, author)

    if mode == 'ordinary':
        if type(data['message']) == list:
            for message in data['message']:
                append_mes_to_delete(author, message)
        else:
            append_mes_to_delete(author, data['message'])
        change_state_characteristic(author, 'current_state', 'None')
        bot = Bot(TOKEN_FOR_BUSINESSMEN)
        await bot.editMessageText(get_text_of_data(author), chat_id=update.message.chat_id,
                                  message_id=get_state(author)['menu'], parse_mode='HTML',
                                  reply_markup=get_buttons(author))
    elif mode == 'invalid_text':
        append_mes_to_delete(author, data['message'])

    elif mode == 'replenishing':
        append_mes_to_delete(author, get_state(author)['menu'])
        await delete_messages(author)
        mes = await update.message.reply_text(get_text_of_data(author),
                                              parse_mode='HTML', reply_markup=get_buttons(author))
        change_state_characteristic(author, 'menu', mes.message_id)
        change_state_characteristic(author, 'current_state', 'None')


async def stop_input_data(update, context):
    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    append_mes_to_delete(author, update.message)
    await delete_messages(author)
    change_state_characteristic(author, 'current_state', 'None')
    mes = await update.message.reply_text(text='Ввод прекращен')
    append_mes_to_delete(author, mes)
    bot = Bot(TOKEN_FOR_BUSINESSMEN)
    await bot.editMessageText(get_text_of_data(author), chat_id=update.message.chat_id,
                              message_id=get_state(author)['menu'],
                              parse_mode='HTML', reply_markup=get_buttons(author))


async def stop_working_with_data(update, author):
    if author.name and author.additional_information and author.email:
        bot = Bot(TOKEN_FOR_BUSINESSMEN)
        await bot.editMessageText(get_text_of_data(author),
                                  chat_id=update.message.chat_id,
                                  message_id=get_state(author)['menu'],
                                  parse_mode='HTML')
        set_state(author, {'state': 'waiting'})
        return 'stopping', {}
    else:
        await update.answer(text='Нельзя завершить процесс, так как не все поля заполнены', show_alert=False)
        return 'stopping', {}
