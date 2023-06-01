from data.menu_class import Menu
from data.change_handlers import *
from telegram import *
from telegram.ext import *


async def create_poll_select_type(update, context):
    if not await is_registered(update, context, who=Author):
        return

    if not check_state({'state': 'waiting'}, update.message.chat_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    buttons = [[InlineKeyboardButton('1_anwser', callback_data=f'sel_type|1'),
                InlineKeyboardButton('many_anwser', callback_data=f'sel_type|2')]]
    mes = await update.message.reply_text(text='Выберите тип опроса',
                                          parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
    set_state(author, {'state': 'selecting_type'})
    append_mes_to_delete(author, mes)


async def create_poll(update, context):
    query = update.callback_query
    _type = get_data_from_button(query)['data'][0]
    author = db_sess.query(Author).filter(Author.telegram_id == query.message.chat_id).first()
    question = Poll1()
    question.balance = 10000000
    question.is_active = False
    question.author = author.id
    db_sess.add(question)
    db_sess.commit()
    await delete_messages(author)
    set_state(author, {'state': 'creating_poll', 'id': question.id, 'current_state': 'None', 'mes_to_delete': ''})

    mes = await query.message.reply_text(text=get_text(author),
                                         parse_mode='HTML', reply_markup=get_buttons(author))
    change_state_characteristic(author, 'menu', mes.message_id)


def get_text(author):
    question = db_sess.query(Poll1).filter(Poll1.id == int(get_state(author)['id'])).first()
    if question.answers:
        answers = "\n"
        for i, answer in enumerate(get_answers_as_list(question)):
            answers += f"    {i + 1}: {answer['answer']}\n"
    else:
        answers = "None"
    return f'All information about this poll:\n\f' \
           f'<b><i>Id:</i></b> {question.id}\n' \
           f'<b><i>Title:</i></b> {question.title}\n' \
           f'<b><i>Text:</i></b> {question.text_of_question}\n' \
           f'<b><i>Additional information:</i></b> {question.additional_information}\n' \
           f'<b><i>Active:</i></b> {"yes" if question.is_active else "no"}\n' \
           f'<b><i>Border date:</i></b> {question.border_date.strftime("%d %B, %Y")}\n' \
           f'<b><i>Needed tags:</i></b> {question.needed_tags.replace(",", ", ") if question.needed_tags else "None"}\n'\
           f'<b><i>Answers:</i></b> {answers}'


def get_buttons(author):
    question = db_sess.query(Poll1).filter(Poll1.id == int(get_state(author)['id'])).first()
    buttons = [[InlineKeyboardButton('Change title' if question.title else 'Add title',
                                     callback_data=f'create_poll|ch_title|{question.id}'),
                InlineKeyboardButton('Change text' if question.text_of_question
                                     else 'Add text', callback_data=f'create_poll|ch_text|{question.id}')],
               [InlineKeyboardButton('Change additional information' if question.additional_information
                                     else 'Add additional information',
                                     callback_data=f'create_poll|ch_inf|{question.id}')],
               [InlineKeyboardButton('Change needed tags' if question.needed_tags
                                     else 'Add needed tags', callback_data=f'create_poll|ch_tags|{question.id}')],
               [InlineKeyboardButton('Append answer', callback_data=f'create_poll|ap_ans|{question.id}'),
                InlineKeyboardButton('Delete answer', callback_data=f'create_poll|del_ans|{question.id}')],
               [InlineKeyboardButton('Activate', callback_data=f'create_poll|activate|{question.id}')],
               [InlineKeyboardButton('Stop', callback_data=f'create_poll|stop|{question.id}')]]

    return InlineKeyboardMarkup(buttons)


async def create_poll_finally(update, author):
    question = db_sess.query(Poll1).filter(Poll1.id == int(get_state(author)['id'])).first()
    if question.title and question.text_of_question and \
            question.additional_information and question.answers:
        question.is_active = True
        db_sess.commit()
        bot = Bot(TOKEN_FOR_BUSINESSMEN)
        await bot.editMessageText(get_text(author),
                                  chat_id=update.message.chat_id,
                                  message_id=get_state(author)['menu'],
                                  parse_mode='HTML')
        set_state(author, {'state': 'waiting'})
        con = sqlite3.connect('db/Results_type_1.db')
        cur = con.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS Poll_{question.id}(
           user_id INTEGER PRIMARY KEY,
           answer_index INTEGER,
           answer_text TEXT,
           date TEXT,
           tags TEXY);
        """)
        con.close()

        return 'stopping', {}
    else:
        await update.answer(text='Нельзя завершить процесс, так как не все поля заполнены', show_alert=False)
        return 'stopping', {}


async def stop_creating(query, author):
    question = db_sess.query(Poll1).filter(Poll1.id == int(get_state(author)['id'])).first()
    db_sess.delete(question)
    set_state(author, {'state': 'waiting'})
    db_sess.commit()
    return 'stop_creating', {}


menu_creating_poll = Menu(menu_type='author', stop_input_name='stop_input_poll_data_creating',
                          callback_states=['creating_poll'])
all_callback_functions = {'ch_title': callback_change_title, 'ch_text': callback_change_text,
                          'ch_inf': callback_change_additional_information,
                          'ch_tags': callback_change_needed_tags,
                          'ap_ans': callback_append_answer, 'del_ans': callback_delete_answer,
                          'activate': create_poll_finally, 'stop': stop_creating}
menu_creating_poll.set_callback_f(all_callback_functions)
all_text_functions = {'changing_title': change_title, 'changing_text': change_text,
                      'changing_additional_information': change_additional_information_poll,
                      'changing_needed_tags': change_needed_tags,
                      'appending_answer': append_answer, 'removing_answer': delete_answer}
menu_creating_poll.set_text_handlers_f(all_text_functions)
menu_creating_poll.set_get_text_f(get_text)
menu_creating_poll.set_get_buttons_f(get_buttons)
