from data.menu_class import Menu
from data.change_handlers import *
from telegram import *
from telegram.ext import *


async def get_one_poll_start(update, context):
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

    set_state(author, {'state': 'getting_poll'})
    await update.message.reply_text(text='Введите тип опроса и id опроса, который'
                                         ' хотите поучить, например 1, 1 значит,'
                                         ' что вы выбрали опрос типа 1 и с индексом 1')


async def get_one_poll(update, context):
    if not await is_registered(update, context, who=Author):
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    if not check_state({'state': 'getting_poll'}, author.telegram_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return
    poll_type, poll_id = list(map(int, update.message.text.split(', ')))
    poll_type = Poll1 if poll_type == 1 else Poll2
    question = db_sess.query(poll_type).filter(poll_type.id == poll_id).first()
    if question is None:
        await update.message.reply_text(text=f'Опроса с индексом {update.message.text} не существует')
        set_state(author, {'state': 'waiting'})
        return
    set_state(author, {'state': 'working_on_poll', 'id': question.id, 'current_state': 'None',
                       'type': 1 if poll_type == Poll1 else 2})

    if question.balance < question.check_per_person:
        question.is_active = False
        db_sess.commit()

    mes = await update.message.reply_text(text=get_text(author),
                                          parse_mode='HTML', reply_markup=get_buttons(author))
    change_state_characteristic(author, 'menu', mes.message_id)


async def stop_working_with_poll(update, author):
    poll_type = Poll1 if get_state(author)['type'] == 1 else Poll2
    question = db_sess.query(poll_type).filter(poll_type.id == int(get_state(author)['id'])).first()
    if question.title and question.text_of_question and question.additional_information:
        return 'stopping', {}
    else:
        await update.answer(text='Нельзя завершить процесс, так как не все поля заполнены', show_alert=False)
        return 'stopping', {}


async def set_activation(query, author):
    poll_type = Poll1 if get_state(author)['type'] == 1 else Poll2
    question = db_sess.query(poll_type).filter(poll_type.id == int(get_state(author)['id'])).first()
    question.is_active = not question.is_active
    db_sess.commit()
    await query.edit_message_text(text=get_text(author), parse_mode='HTML',
                                  reply_markup=get_buttons(author))
    return 'change_activation', {}


def get_text(author):
    poll_type = Poll1 if get_state(author)['type'] == 1 else Poll2
    question = db_sess.query(poll_type).filter(poll_type.id == int(get_state(author)['id'])).first()
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


def get_buttons(author):
    poll_type = Poll1 if get_state(author)['type'] == 1 else Poll2
    question = db_sess.query(poll_type).filter(poll_type.id == int(get_state(author)['id'])).first()
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


menu_working_on_poll = Menu(menu_type='author', stop_input_name='stop_input_poll_data',
                            callback_states=['registration', 'working_on_poll'])
all_callback_functions = {'ch_title': callback_change_title, 'ch_text': callback_change_text,
                          'ch_inf': callback_change_additional_information, 'ch_tags': callback_change_needed_tags,
                          'res_by_tags': callback_get_results_by_tags, 'activate': set_activation,
                          'deactivate': set_activation, 'stop': stop_working_with_poll}
menu_working_on_poll.set_callback_f(all_callback_functions)
all_text_functions = {'changing_title': change_title, 'changing_text': change_text,
                      'changing_additional_information': change_additional_information_poll,
                      'changing_needed_tags': change_needed_tags, 'None': invalid_text,
                      'getting_results_by_tags': get_results_by_tags}
menu_working_on_poll.set_text_handlers_f(all_text_functions)
menu_working_on_poll.set_get_text_f(get_text)
menu_working_on_poll.set_get_buttons_f(get_buttons)
