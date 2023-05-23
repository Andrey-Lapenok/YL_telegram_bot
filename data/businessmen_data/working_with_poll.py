import asyncio
from telegram import *
from telegram.ext import *
from orm_support.all_db_models import *
from data.base import *
from data.change_handlers import *
import datetime


async def get_one_poll_start(update, context):
    if not await is_registered(update, context, who=Author):
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    if not check_state({'state': 'waiting'}, author.telegram_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    questions = db_sess.query(Question).filter(Question.author == author.id).all()
    if len(questions) <= 0:
        await update.message.reply_text(text='У вас нет ни одного опроса, вы можете создать их с помощью команды '
                                             '<b><i>/create_poll</i></b>', parse_mode='HTML')
        return

    text_of_mes = 'Все ваши опросы:\n'
    for index, question in enumerate(questions):
        text_of_mes += f'    {index + 1}. {question.title} (id: {question.id},' \
                       f' {"active" if question.is_active else "not active"})\n'

    await update.message.reply_text(text=text_of_mes)

    set_state(author, {'state': 'getting_poll'})
    await update.message.reply_text(text='Введите id опроса, который хотите поучить')


async def get_one_poll(update, context):
    if not await is_registered(update, context, who=Author):
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    if not check_state({'state': 'getting_poll'}, author.telegram_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    question = db_sess.query(Question).filter(Question.id == int(update.message.text)).first()
    set_state(author, {'state': 'working_on_poll', 'id': question.id, 'current_state': 'None'})

    if question.balance < question.check_per_person:
        question.is_active = False
        db_sess.commit()

    mes = await update.message.reply_text(text=get_text_for_information_about_poll(question),
                                          parse_mode='HTML', reply_markup=get_buttons(question))
    change_state_characteristic(author, 'menu', mes.message_id)


async def callback_handler_working_on_poll(update, context):
    query = update.callback_query
    data = get_data_from_button(query)['data'][0]
    author = db_sess.query(Author).filter(Author.telegram_id == query.message.chat_id).first()
    question = db_sess.query(Question).filter(Question.id == int(get_data_from_button(query)['data'][1])).first()
    await asyncio.create_task(delete_messages(author))
    if not check_state({'state': 'working_on_poll'}, author.telegram_id, who=Author):
        await query.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        await query.edit_message_text(text=get_text_for_information_about_poll(question), parse_mode='HTML')
        return

    all_functions = {'ch_title': callback_change_title, 'ch_text': callback_change_text,
                     'ch_inf': callback_change_additional_information, 'ch_tags': callback_change_needed_tags,
                     'res_by_tags': callback_get_results_by_tags, 'activate': set_activation,
                     'deactivate': set_activation, 'stop': stop_working_with_poll}

    mode, data = await all_functions[data](query, author)
    if mode == 'ordinary':
        markup = ReplyKeyboardMarkup([['/stop_input_data_about_poll']], one_time_keyboard=False)
        mes = await query.message.reply_text(
            text="Нажмите на кнопку <b><i>/stop_input_data_about_poll</i></b>, если хотите прекратить ввод",
            parse_mode='HTML', reply_markup=markup)
        append_mes_to_delete(author, mes)
        if type(data['message']) == list:
            for message in data['message']:
                append_mes_to_delete(author, message)
        else:
            append_mes_to_delete(author, data['message'])
        await query.edit_message_text(text=get_text_for_information_about_poll(question), parse_mode='HTML')
    elif mode == 'stopping':
        return
    elif mode == 'change_activation':
        return


def get_buttons(question):
    buttons = [[InlineKeyboardButton('Change title', callback_data=f'work_poll|ch_title|{question.id}'),
                InlineKeyboardButton('Change text', callback_data=f'work_poll|ch_text|{question.id}')],
               [InlineKeyboardButton('Change additional information', callback_data=f'work_poll|ch_inf|{question.id}')],
               [InlineKeyboardButton('Change needed tags', callback_data=f'work_poll|ch_tags|{question.id}')]]
    if question.border_date < datetime.datetime.now() or question.balance < question.check_per_person:
        pass
    elif not question.is_active:
        buttons.append([InlineKeyboardButton('Activate', callback_data=f'work_poll|activate|{question.id}')])
    else:
        buttons.append([InlineKeyboardButton('Deactivate', callback_data=f'work_poll|deactivate|{question.id}')])

    buttons.append([InlineKeyboardButton('Get results by tags', callback_data=f'work_poll|res_by_tags|{question.id}')])
    buttons.append([InlineKeyboardButton('Replenish the balance', callback_data=f'work_poll|rep_bal|{question.id}')])
    buttons.append([InlineKeyboardButton('Stop', callback_data=f'work_poll|stop|{question.id}')])
    return InlineKeyboardMarkup(buttons)


def get_text_for_information_about_poll(question):
    results = '\n'
    all_votes = sum(list(map(lambda x: int(x.split(":")[1]), question.answers.split('|'))))
    if all_votes == 0:
        results = 'None'
    else:
        for answer in question.answers.split('|'):
            results += f'    {answer.split(":")[0]}: {round(int(answer.split(":")[1]) / all_votes * 100, 2)}%\n'

    return f'All information about this poll:\n\f' \
           f'<b><i>Id:</i></b> {question.id}\n' \
           f'<b><i>Title:</i></b> {question.title}\n' \
           f'<b><i>Text:</i></b> {question.text_of_question}\n' \
           f'<b><i>Additional information:</i></b> {question.additional_information}\n' \
           f'<b><i>Active:</i></b> {"yes" if question.is_active else "no"}\n' \
           f'<b><i>Border date:</i></b> {question.border_date.strftime("%d %B, %Y")}\n' \
           f'<b><i>Needed' \
           f' tags:</i></b> {question.needed_tags.replace(",", ", ") if question.needed_tags else "None"}\n' \
           f'<b><i>Balance:</i></b> {question.balance} rubles\n' \
           f'<b><i>Money for one:</i></b> {question.check_per_person} rubles\n' \
           f'<b><i>Remaining quantity:</i></b> {question.balance // question.check_per_person}\n' \
           f'<b><i>Results:</i></b>{results}'


async def text_handler_working_on_poll(update, context):
    all_functions = {'changing_title': change_title, 'changing_text': change_text,
                     'changing_additional_information': change_additional_information,
                     'changing_needed_tags': change_needed_tags, 'None': invalid_text,
                     'getting_results_by_tags': get_results_by_tags}
    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    question = db_sess.query(Question).filter(Question.id == int(get_state(author)['id'])).first()

    append_mes_to_delete(author, update.message)
    await asyncio.create_task(delete_messages(author))

    current_state = get_state(author)['current_state']
    mode, data = await all_functions[current_state](update, question)

    if mode == 'ordinary':
        if type(data['message']) == list:
            for message in data['message']:
                append_mes_to_delete(author, message)
        else:
            append_mes_to_delete(author, data['message'])
        change_state_characteristic(author, 'current_state', 'None')
        bot = Bot(TOKEN_FOR_BUSINESSMEN)
        await bot.editMessageText(get_text_for_information_about_poll(question), chat_id=update.message.chat_id,
                                  message_id=get_state(author)['menu'], parse_mode='HTML',
                                  reply_markup=get_buttons(question))
    elif mode == 'invalid_text':
        append_mes_to_delete(author, data['message'])


async def set_activation(query, author):
    question = db_sess.query(Question).filter(Question.id == int(get_state(author)['id'])).first()
    question.is_active = not question.is_active
    db_sess.commit()
    await query.edit_message_text(text=get_text_for_information_about_poll(question), parse_mode='HTML',
                                  reply_markup=get_buttons(question))
    return 'change_activation', {}


async def stop_input_data_about_poll(update, context):
    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    question = db_sess.query(Question).filter(Question.id == int(get_state(author)['id'])).first()
    append_mes_to_delete(author, update.message)
    await delete_messages(author)
    change_state_characteristic(author, 'current_state', 'None')
    mes = await update.message.reply_text(text='Ввод прекращен')
    append_mes_to_delete(author, mes)
    bot = Bot(TOKEN_FOR_BUSINESSMEN)
    await bot.editMessageText(get_text_for_information_about_poll(question), chat_id=update.message.chat_id,
                              message_id=get_state(author)['menu'], parse_mode='HTML',
                              reply_markup=get_buttons(question))


async def stop_working_with_poll(update, author):
    question = db_sess.query(Question).filter(Question.id == int(get_state(author)['id'])).first()
    if question.title and question.text_of_question and question.additional_information:
        bot = Bot(TOKEN_FOR_BUSINESSMEN)
        await bot.editMessageText(get_text_for_information_about_poll(question),
                                  chat_id=update.message.chat_id,
                                  message_id=get_state(author)['menu'],
                                  parse_mode='HTML')
        set_state(author, {'state': 'waiting'})
        return 'stopping', {}
    else:
        await update.answer(text='Нельзя завершить процесс, так как не все поля заполнены', show_alert=False)
        return 'stopping', {}
