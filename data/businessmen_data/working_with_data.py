from data.menu_class import Menu
from data.change_handlers import *
from telegram import *
from telegram.ext import *


async def get_all_data(update, context):
    if not await is_registered(update, context, who=Author):
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    if not check_state({'state': 'waiting'}, author.telegram_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    set_state(author, {'state': 'working_with_data', 'current_state': 'None', 'mes_to_delete': ''})
    mes = await update.message.reply_text(text=get_text(author),
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
    mes = await update.message.reply_text(text=get_text(author),
                                          parse_mode='HTML', reply_markup=get_buttons(author))
    change_state_characteristic(author, 'menu', mes.message_id)


def get_text(author):
    return f'<i><b>Name:</b></i> {author.name}\n'\
           f'<i><b>Additional information:</b></i> {author.additional_information}\n'\
           f'<i><b>Email:</b></i> {author.email}\n' \
           f'<i><b>Balance:</b></i> {author.balance} rubles'


def get_buttons(author):
    buttons = [[InlineKeyboardButton('Change name', callback_data=f'work_data|ch_name'),
                InlineKeyboardButton('Change email', callback_data=f'work_data|ch_email')],
               [InlineKeyboardButton('Change additional information', callback_data=f'work_data|ch_inf')],
               [InlineKeyboardButton('Replenish balance', callback_data=f'work_data|rep_bal')]]

    if get_state(author)['state'] == 'registration':
        buttons.append([InlineKeyboardButton('Accept', callback_data='work_data|stop')])
    else:
        buttons.append([InlineKeyboardButton('Stop', callback_data='work_data|stop')])

    return InlineKeyboardMarkup(buttons)


async def stop_working_with_data(update, author):
    if author.name and author.additional_information and author.email:
        bot = Bot(TOKEN_FOR_BUSINESSMEN)
        await bot.editMessageText(get_text(author),
                                  chat_id=update.message.chat_id,
                                  message_id=get_state(author)['menu'],
                                  parse_mode='HTML')
        set_state(author, {'state': 'waiting'})
        return 'stopping', {}
    else:
        await update.answer(text='Нельзя завершить процесс, так как не все поля заполнены', show_alert=False)
        return 'stopping', {}


menu_working_on_inf = Menu(menu_type='author', stop_input_name='stop_input',
                           callback_states=['registration', 'working_with_data'])
all_callback_functions = {'ch_name': callback_change_name, 'ch_inf': callback_change_additional_information,
                          'ch_email': callback_change_email, 'rep_bal': callback_replenish_balance,
                          'stop': stop_working_with_data}
menu_working_on_inf.set_callback_f(all_callback_functions)
all_text_functions = {'changing_name': change_name, 'changing_email': change_email,
                      'changing_additional_information': change_additional_information,
                      'replenishing_balance': replenish_balance, 'None': invalid_text}
menu_working_on_inf.set_text_handlers_f(all_text_functions)
menu_working_on_inf.set_get_text_f(get_text)
menu_working_on_inf.set_get_buttons_f(get_buttons)
