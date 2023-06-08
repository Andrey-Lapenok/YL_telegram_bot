from data.base import *
import asyncio
from telegram import *
from telegram.ext import *


class Menu:
    def __init__(self, callback_functions=None, text_functions=None, get_text_f=None, get_buttons_f=None,
                 stop_input_name=None, menu_type=None, callback_states=None):
        self.callback_functions = callback_functions
        self.text_functions = text_functions
        self.get_text = get_text_f
        self.get_buttons = get_buttons_f
        self.stop_input_name = stop_input_name
        self.menu_type = menu_type
        self.callback_states = callback_states

    def set_callback_f(self, callback_functions):
        self.callback_functions = callback_functions

    def set_text_handlers_f(self, text_functions):
        self.text_functions = text_functions

    def set_get_text_f(self, get_text_f):
        self.get_text = get_text_f

    def set_get_buttons_f(self, get_buttons_f):
        self.get_buttons = get_buttons_f

    def set_stop_input(self, stop_input_name):
        self.stop_input_name = stop_input_name

    async def callback_handler(self, update, context):
        query = update.callback_query
        data = get_data_from_button(query)['data'][0]
        person_type = OurUser if self.menu_type == 'user' else Author
        person = db_sess.query(person_type).filter(person_type.telegram_id == query.message.chat_id).first()
        await asyncio.create_task(delete_messages(person))
        if not any(check_state({'state': state},
                               person.telegram_id, who=person_type) for state in self.callback_states):
            await query.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
            await query.edit_message_text(text=self.get_text(person), parse_mode='HTML')
            return

        mode, data = await self.callback_functions[data](query, person)

        if mode == 'ordinary':
            markup = ReplyKeyboardMarkup([[f'/{self.stop_input_name}']], one_time_keyboard=False)
            mes = await query.message.reply_text(
                text=f"Нажмите на кнопку <b><i>/{self.stop_input_name}</i></b>, если хотите прекратить ввод",
                parse_mode='HTML', reply_markup=markup)
            append_mes_to_delete(person, mes)
            if type(data['message']) == list:
                for message in data['message']:
                    append_mes_to_delete(person, message)
            else:
                append_mes_to_delete(person, data['message'])
            await query.edit_message_text(text=self.get_text(person), parse_mode='HTML')
        elif mode == 'stopping':
            await query.edit_message_text(text=self.get_text(person), parse_mode='HTML')
            set_state(person, {'state': 'waiting'})
        elif mode == 'stop_creating':
            await query.edit_message_text(text=self.get_text(person), parse_mode='HTML')
            set_state(person, {'state': 'waiting'})

    async def text_handler(self, update, context):
        person_type = OurUser if self.menu_type == 'user' else Author
        person = db_sess.query(person_type).filter(person_type.telegram_id == update.message.chat_id).first()
        append_mes_to_delete(person, update.message)
        await delete_messages(person)

        current_state = get_state(person)['current_state']
        mode, data = await self.text_functions[current_state](update, person)

        if mode == 'ordinary':
            if type(data['message']) == list:
                for message in data['message']:
                    append_mes_to_delete(person, message)
            else:
                append_mes_to_delete(person, data['message'])
            change_state_characteristic(person, 'current_state', 'None')
            bot = Bot(TOKEN if self.menu_type == 'user' else TOKEN_FOR_BUSINESSMEN)
            await bot.editMessageText(self.get_text(person), chat_id=update.message.chat_id,
                                      message_id=get_state(person)['menu'], parse_mode='HTML',
                                      reply_markup=self.get_buttons(person))
        elif mode == 'invalid_text':
            append_mes_to_delete(person, data['message'])

        elif mode == 'replenishing':
            append_mes_to_delete(person, get_state(person)['menu'])
            await delete_messages(person)
            mes = await update.message.reply_text(self.get_text(person),
                                                  parse_mode='HTML', reply_markup=self.get_buttons(person))
            change_state_characteristic(person, 'menu', mes.message_id)
            change_state_characteristic(person, 'current_state', 'None')

    async def stop_input_data(self, update, context):
        person_type = OurUser if self.menu_type == 'user' else Author
        person = db_sess.query(person_type).filter(person_type.telegram_id == update.message.chat_id).first()
        append_mes_to_delete(person, update.message)
        await delete_messages(person)
        change_state_characteristic(person, 'current_state', 'None')
        mes = await update.message.reply_text(text='Ввод прекращен')
        append_mes_to_delete(person, mes)
        bot = Bot(TOKEN if person_type == OurUser else TOKEN_FOR_BUSINESSMEN)
        await bot.editMessageText(self.get_text(person), chat_id=update.message.chat_id,
                                  message_id=get_state(person)['menu'],
                                  parse_mode='HTML', reply_markup=self.get_buttons(person))
