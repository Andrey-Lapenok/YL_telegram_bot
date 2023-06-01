from data.menu_class import Menu
from data.change_handlers import *
from telegram import *
from telegram.ext import *


async def get_all_data(update, context):
    if not await is_registered(update, context):
        return

    if not check_state({'state': 'waiting'}, update.message.chat_id):
        await update.message.reply_text('Вы не можете начать новое действие, не закончив старое')
        return

    user = db_sess.query(OurUser).filter(OurUser.telegram_id == update.message.chat_id).first()
    set_state(user, {'state': 'working_with_data', 'current_state': 'None'})

    mes = await update.message.reply_text(text=get_text(user),
                                          parse_mode='HTML', reply_markup=get_buttons(user))
    change_state_characteristic(user, 'menu', mes.message_id)


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

    mes = await update.message.reply_text(text=get_text(user),
                                          parse_mode='HTML', reply_markup=get_buttons(user))
    change_state_characteristic(user, 'menu', mes.message_id)


async def stop_working_with_inf(update, user):
    if user.name and user.surname and user.additional_information:
        bot = Bot(TOKEN)
        await bot.editMessageText(menu_working_on_inf.get_text(user),
                                  chat_id=update.message.chat_id,
                                  message_id=get_state(user)['menu'],
                                  parse_mode='HTML')
        set_state(user, {'state': 'ready'})
        return 'stopping', {}
    else:
        await update.answer(text='Нельзя завершить процесс, так как не все поля заполнены', show_alert=False)
        return 'stopping', {}


def get_text(user):
    return f'<i><b>Name:</b></i> {user.name}\n' \
           f'<i><b>Surname:</b></i> {user.surname}\n' \
           f'<i><b>Additional information:</b></i> {user.additional_information}\n' \
           f'<i><b>Tags:</b></i> {user.tags.replace(",", ", ") if user.tags else "None"}\n' \
           f'<i><b>Waiting time:</b></i> {user.waiting_time} minutes\n' \
           f'<i><b>Balance</b></i> {user.balance} rubles'


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


menu_working_on_inf = Menu(menu_type='user', stop_input_name='stop_input',
                           callback_states=['registration', 'working_with_data'])
all_callback_functions = {'ch_name': callback_change_name, 'ch_surname': callback_change_surname,
                          'ch_inf': callback_change_additional_information, 'ch_time': callback_change_waiting_time,
                          'ch_tags': callback_change_tags, 'ap_tags': callback_append_tags,
                          'del_tags': callback_delete_tags, 'stop': stop_working_with_inf}
menu_working_on_inf.set_callback_f(all_callback_functions)
all_text_functions = {'changing_name': change_name, 'changing_surname': change_surname,
                      'changing_additional_information': change_additional_information,
                      'changing_waiting_time': change_waiting_time, 'changing_tags': change_tags,
                      'appending_tags': append_tags, 'removing_tags': remove_tags,
                      'None': invalid_text}
menu_working_on_inf.set_text_handlers_f(all_text_functions)
menu_working_on_inf.set_get_text_f(get_text)
menu_working_on_inf.set_get_buttons_f(get_buttons)
