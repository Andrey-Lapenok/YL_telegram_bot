import asyncio

from telegram import *
from telegram.ext import *
from orm_support.all_db_models import *
from data.base import *
from data.change_handlers import *
import datetime


async def create_poll(update, context):
    if not await is_registered(update, context, who=Author):
        return

    if not check_state({'state': 'waiting'}, update.message.chat_id, who=Author):
        await update.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        return

    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    question = Question()
    question.is_active = False
    question.author = author.id
    db_sess.add(question)
    db_sess.commit()
    set_state(author, {'state': 'creating_poll', 'id': question.id, 'current_state': 'None', 'mes_to_delete': ''})

    await update.message.reply_text(text=get_text_for_information_about_poll(question),
                                    parse_mode='HTML', reply_markup=get_buttons(question))


async def callback_handler_creating_poll(update, context):
    query = update.callback_query
    data = get_data_from_button(query)['data'][0]
    author = db_sess.query(Author).filter(Author.telegram_id == query.message.chat_id).first()
    question = db_sess.query(Question).filter(Question.id == int(get_data_from_button(query)['data'][1])).first()
    if not check_state({'state': 'creating_poll'}, author.telegram_id, who=Author):
        await query.message.reply_text(text='Вы не можете начать новое действие, не закончив старое')
        await query.edit_message_text(text=get_text_for_information_about_poll(question), parse_mode='HTML')
        return

    await asyncio.create_task(delete_messages(author))

    if data == 'activate':
        if question.title and question.text_of_question and \
                question.additional_information and question.answers:
            question.is_active = True
            db_sess.commit()
            await query.edit_message_text(text=get_text_for_information_about_poll(question), parse_mode='HTML')
            set_state(author, {'state': 'waiting'})

            with open(f'db/results/{question.id}.csv', 'w', newline='', encoding="utf8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=header_of_vote_files,
                    delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()

            return
        else:
            await context.bot.answer_callback_query(callback_query_id=query.id,
                                                    text='Нельзя завершить процесс, так как не все поля заполнены',
                                                    show_alert=True)
            return

    markup = ReplyKeyboardMarkup([['/stop_input_data_about_poll_creating']], one_time_keyboard=False)
    mes = await query.message.reply_text(
        text="Нажмите на кнопку <b><i>/stop_input_data_about_poll_creating</i></b>, если хотите прекратить ввод",
        parse_mode='HTML', reply_markup=markup)
    append_mes_to_delete(author, mes)

    all_functions = {'ch_title': callback_change_title, 'ch_text': callback_change_text,
                     'ch_inf': callback_change_additional_information,
                     'ch_tags': callback_change_needed_tags,
                     'ap_ans': callback_append_answer, 'del_ans': callback_delete_answer}

    mes = await all_functions[data](query, author)

    append_mes_to_delete(author, mes)
    append_mes_to_delete(author, query.message)
    await query.edit_message_text(text=get_text_for_information_about_poll(question), parse_mode='HTML')

    return


def get_buttons(question):
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
               [InlineKeyboardButton('Activate', callback_data=f'create_poll|activate|{question.id}')]]

    return InlineKeyboardMarkup(buttons)


def get_text_for_information_about_poll(question):
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


async def text_handler_creating_poll(update, context):
    all_functions = {'changing_title': change_title, 'changing_text': change_text,
                     'changing_additional_information': change_additional_information,
                     'changing_needed_tags': change_needed_tags,
                     'appending_answer': append_answer, 'removing_answer': delete_answer}
    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    question = db_sess.query(Question).filter(Question.id == int(get_state(author)['id'])).first()

    append_mes_to_delete(author, update.message)
    await asyncio.create_task(delete_messages(author))

    current_state = get_state(author)['current_state']
    mes = await all_functions[current_state](update, question)
    append_mes_to_delete(author, mes)

    change_state_characteristic(author, 'current_state', 'None')
    await update.message.reply_text(text=get_text_for_information_about_poll(question),
                                    parse_mode='HTML', reply_markup=get_buttons(question))


async def stop_input_data_about_poll_creating(update, context):
    author = db_sess.query(Author).filter(Author.telegram_id == update.message.chat_id).first()
    question = db_sess.query(Question).filter(Question.id == int(get_state(author)['id'])).first()
    append_mes_to_delete(author, update.message)
    await delete_messages(author)
    change_state_characteristic(author, 'current_state', 'None')
    mes = await update.message.reply_text(text='Ввод прекращен')
    append_mes_to_delete(author, mes)
    await update.message.reply_text(text=get_text_for_information_about_poll(question),
                                    parse_mode='HTML', reply_markup=get_buttons(question))
