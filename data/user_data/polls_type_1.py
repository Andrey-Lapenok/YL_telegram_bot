from telegram import *
from telegram.ext import *
from data.base import *
import sqlite3


def get_reply_markup_type_1(question, user, _type):
    answers = get_answers_as_list(question)
    buttons = []
    if question.id not in get_answers_of_user(user, '1'):
        if len(answers) > 2:
            buttons = [
                [InlineKeyboardButton(answer['answer'],
                                      callback_data=f'type_1|answer|{question.id}|{answers.index(answer)}')]
                for answer in answers]
        else:
            buttons = [
                [InlineKeyboardButton(answer['answer'],
                                      callback_data=f'type_1|answer|{question.id}|{answers.index(answer)}')
                 for answer in answers]]

    if _type == 'get_information':
        buttons.append([InlineKeyboardButton('ℹ️informationℹ', callback_data=f'type_1|information|{question.id}')])

    elif _type == 'delete_information':
        buttons.append([InlineKeyboardButton('ℹ️delete informationℹ',
                                             callback_data=f'type_1|d_information|{question.id}')])
    return InlineKeyboardMarkup(buttons)


def get_text_type_1(poll, user):
    answer = get_vote_as_dict(poll.id, user, 1 if type(poll) == Poll1 else 2)
    if answer is not None:
        return f'Вы выбрали: <b><i>{answer["answer_text"]}</i></b>'
    return ''


def set_answer_1(question, answer):
    answers = get_answers_as_dict(question)
    answers[answer] += 1
    question.answers = '|'.join(list(map(lambda x: f'{x}:{answers[x]}', answers)))
    db_sess.commit()


async def callback_1(query):
    question_id, number_of_answer = get_data_from_button(query)['data'][1:]
    number_of_answer = int(number_of_answer)
    question = db_sess.query(Poll1).filter(Poll1.id == question_id).first()
    user = db_sess.query(OurUser).filter(OurUser.telegram_id == query.message.chat_id).first()

    user.balance += question.check_per_person
    db_sess.commit()

    answer = get_answers_as_list(question)[number_of_answer]['answer']
    set_answer_1(question, answer)

    con = sqlite3.connect('db/Results_type_1.db')
    cur = con.cursor()
    cur.execute(f"""INSERT INTO Poll_{question.id}(user_id, answer_index, answer_text, date, tags)
                        VALUES(?, ?, ?, ?, ?);""", (user.id, number_of_answer, answer,
                                                    datetime.datetime.now().strftime('%Y-%m-%d'), user.tags))
    con.commit()
    con.close()

    await query.edit_message_text(text=f"{question.text_of_question}\n" + get_text_type_1(question, user),
                                  parse_mode='HTML', reply_markup=get_reply_markup_type_1(question, user,
                                                                                          _type='get_information'))
