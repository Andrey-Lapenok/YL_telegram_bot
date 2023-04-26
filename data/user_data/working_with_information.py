import asyncio
from telegram import *
from telegram.ext import *
from orm_support.all_db_models import *
from data.base import *
from data.change_handlers import *
import datetime


async def get_all_data(update, context):
    if not await is_registered(update, context):
        return

    if not check_state({'state': 'waiting'}, update.message.chat_id):
        await update.message.send_message(text='Вы не можете начать новое действие, не закончив старое')
        return

    user = db_sess.query(OurUser).filter(OurUser.telegram_id == update.message.chat_id).first()
    set_state(user, {'state': 'working_with_data', 'current_state': 'None'})

    await update.message.reply_text(text=get_text_of_data(user),
                                    parse_mode='HTML', reply_markup=get_buttons(user))


async def registrate(update, context):
    user = db_sess.query(OurUser).filter(OurUser.telegram_id == update.message.chat_id).first()
    if not user:
        user = OurUser()
        user.telegram_id = update.message.chat_id
        db_sess.add(user)
        db_sess.commit()

    else:
        await update.message.reply_text(text=' Вы уже зарегистрированы, воспользуйтесь <i><b>/help</b></i>,'
                                             ' чтобы увидеть все возможности', parse_mode='HTML')
        return

    set_state(user, {'state': 'registration', 'current_state': 'None', 'mes_to_delete': ''})

    await update.message.reply_text(text=get_text_of_data(user),
                                    parse_mode='HTML', reply_markup=get_buttons(user))


async def callback_handler_working_with_data(update, context):
    query = update.callback_query
    user = db_sess.query(OurUser).filter(OurUser.telegram_id == query.message.chat_id).first()

    await asyncio.create_task(delete_messages(user))
    if not check_state({'state': 'working_with_data'}, query.message.chat_id) and not check_state(
            {'state': 'registration'}, query.message.chat_id):
        await query.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        await query.edit_message_text(text=get_text_of_data(user), parse_mode='HTML')
        return

    data = get_data_from_button(query)['data'][0]
    if data == 'stop':
        if user.name and user.surname and user.additional_information:
            await query.edit_message_text(text=get_text_of_data(user), parse_mode='HTML')
            set_state(user, {'state': 'waiting'})
            return
        else:
            await context.bot.answer_callback_query(callback_query_id=query.id,
                                                    text='Нельзя завершить процесс, так как не все поля заполнены',
                                                    show_alert=True)
            return

    markup = ReplyKeyboardMarkup([['/stop_input']], one_time_keyboard=False)
    mes = await query.message.reply_text(text="Нажмите на кнопку <b><i>/stop_input</i></b>, если хотите прекратить ввод",
                                         parse_mode='HTML', reply_markup=markup)
    append_mes_to_delete(user, mes)

    all_functions = {'ch_name': callback_change_name, 'ch_surname': callback_change_surname,
                     'ch_inf': callback_change_additional_information, 'ch_time': callback_change_waiting_time,
                     'ch_tags': callback_change_tags, 'ap_tags': callback_append_tags,
                     'del_tags': callback_delete_tags}

    mes = await all_functions[data](query, user)
    append_mes_to_delete(user, mes)
    append_mes_to_delete(user, query.message)

    await query.edit_message_text(text=get_text_of_data(user), parse_mode='HTML')


def get_buttons(user):
    buttons = [[InlineKeyboardButton('Add name' if not user.name else 'Change name', callback_data=f'work_inf|ch_name'),
                InlineKeyboardButton('Add surname' if not user.surname else
                                     'Change surname', callback_data=f'work_inf|ch_surname')],
               [InlineKeyboardButton('Add additional information' if not user.additional_information else
                                     'Change additional information', callback_data=f'work_inf|ch_inf')],
               [InlineKeyboardButton('Add tags' if not user.tags else
                                     'Change tags', callback_data=f'work_inf|ch_tags')],
               [InlineKeyboardButton('Append tags', callback_data=f'work_inf|ap_tags'),
               InlineKeyboardButton('Delete tags', callback_data=f'work_inf|del_tags')],
               [InlineKeyboardButton('Add waiting time' if not user.waiting_time else
                                     'Change waiting time', callback_data=f'work_inf|ch_time')]]

    if get_state(user)['state'] == 'working_with_data':
        buttons.append([InlineKeyboardButton('Stop', callback_data='work_inf|stop')])
    if get_state(user)['state'] == 'registration':
        buttons.append([InlineKeyboardButton('Registrate', callback_data='work_inf|stop')])

    return InlineKeyboardMarkup(buttons)


def get_text_of_data(user):
    return f'<i><b>Name:</b></i> {user.name}\n' \
           f'<i><b>Surname:</b></i> {user.surname}\n' \
           f'<i><b>Additional information:</b></i> {user.additional_information}\n' \
           f'<i><b>Tags:</b></i> {user.tags.replace(",", ", ") if user.tags else "None"}\n' \
           f'<i><b>Waiting time:</b></i> {user.waiting_time} minutes'


async def text_handler_working_with_data(update, context):
    all_functions = {'changing_name': change_name, 'changing_surname': change_surname,
                     'changing_additional_information': change_additional_information,
                     'changing_waiting_time': change_waiting_time, 'changing_tags': change_tags,
                     'appending_tags': append_tags, 'removing_tags': remove_tags,
                     'None': invalid_text}
    user = db_sess.query(OurUser).filter(OurUser.telegram_id == update.message.chat_id).first()
    append_mes_to_delete(user, update.message)
    await asyncio.create_task(delete_messages(user))

    current_state = get_state(user)['current_state']
    mes = await all_functions[current_state](update, user)
    append_mes_to_delete(user, mes)

    change_state_characteristic(user, 'current_state', 'None')
    await update.message.reply_text(text=get_text_of_data(user),
                                    parse_mode='HTML', reply_markup=get_buttons(user))


async def stop_work_with_inf(update, context):
    user = db_sess.query(OurUser).filter(OurUser.telegram_id == update.message.chat_id).first()
    append_mes_to_delete(user, update.message)
    await delete_messages(user)
    change_state_characteristic(user, 'current_state', 'None')
    mes = await update.message.reply_text(text='Ввод прекращен')
    append_mes_to_delete(user, mes)
    await update.message.reply_text(text=get_text_of_data(user),
                                    parse_mode='HTML', reply_markup=get_buttons(user))

