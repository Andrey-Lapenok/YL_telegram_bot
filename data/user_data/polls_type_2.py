from telegram import *
from telegram.ext import *
from data.base import *
import sqlite3


def get_reply_markup_type_2(question, user, _type):
    answers = get_answers_as_list(question)
    buttons = []
    if question.id not in get_answers_of_user(user, '2'):
        all_answers_of_user = get_vote_as_dict(question.id, user, 2)
        if all_answers_of_user is not None:
            all_answers_of_user = all_answers_of_user['answer_text'].split('|')
        else:
            all_answers_of_user = []
        if len(answers) > 2:
            buttons = [
                [InlineKeyboardButton(answer['answer'] + ('✅' if answer['answer'] in all_answers_of_user else ''),
                                      callback_data=f'type_2|add_answer|{question.id}|{answers.index(answer)}')]
                for answer in answers]
        else:
            buttons = [
                [InlineKeyboardButton(answer['answer'] + ('✅' if answer['answer'] in all_answers_of_user else ''),
                                      callback_data=f'type_2|add_answer|{question.id}|{answers.index(answer)}')
                 for answer in answers]]

        if get_vote_as_dict(question.id, user, 2) and get_vote_as_dict(question.id, user, 2)['answer_text'] != '':
            buttons.append([InlineKeyboardButton('answer', callback_data=f'type_2|answer|{question.id}')])

    if _type == 'get_information':
        buttons.append([InlineKeyboardButton('ℹ️informationℹ', callback_data=f'type_2|information|{question.id}')])

    elif _type == 'delete_information':
        buttons.append([InlineKeyboardButton('ℹ️delete informationℹ',
                                             callback_data=f'type_2|d_information|{question.id}')])
    return InlineKeyboardMarkup(buttons)


def get_text_type_2(poll, user):
    answer = get_vote_as_dict(poll.id, user, 1 if type(poll) == Poll1 else 2)
    if answer is not None and answer["answer_text"] != '':
        text_of_mes = "".join(["\n    - " + i for i in answer["answer_text"].split("|")])
        return f'Вы выбрали: {text_of_mes}'
    return ''


def change_vote(poll, user, answer_id, answer_text):
    vote = get_vote_as_dict(poll.id, user, 2)
    answers = get_answers_as_dict(poll)
    con = sqlite3.connect('db/Results_type_2.db')
    cur = con.cursor()
    if answer_text in vote['answer_text'].split('|'):
        answers[answer_text] -= 1
        poll.answers = '|'.join(list(map(lambda x: f'{x}:{answers[x]}', answers)))
        new_answer_id = vote['answer_index'].split('|') if vote['answer_index'] != '' else []
        new_answer_id.remove(str(answer_id))
        new_answer_text = vote['answer_text'].split('|') if vote['answer_text'] != '' else []
        new_answer_text.remove(answer_text)

    else:
        answers[answer_text] += 1
        poll.answers = '|'.join(list(map(lambda x: f'{x}:{answers[x]}', answers)))
        new_answer_id = vote['answer_index'].split('|') if vote['answer_index'] != '' else []
        new_answer_id.append(str(answer_id))
        new_answer_text = vote['answer_text'].split('|') if vote['answer_text'] != '' else []
        new_answer_text.append(answer_text)

    cur.execute(f"""UPDATE Poll_{poll.id} SET answer_index = ?, answer_text = ? WHERE user_id = {user.id}""",
                ('|'.join(new_answer_id), '|'.join(new_answer_text)))
    con.commit()
    con.close()
    db_sess.commit()


async def callback_2(query):
    type_of_query, question_id = get_data_from_button(query)['data'][:2]
    question = db_sess.query(Poll2).filter(Poll2.id == question_id).first()
    user = db_sess.query(OurUser).filter(OurUser.telegram_id == query.message.chat_id).first()

    if type_of_query == 'answer':
        append_answered_poll(user, question, 2)
        user.balance += question.check_per_person
        db_sess.commit()

    elif type_of_query == 'add_answer':
        number_of_answer = int(get_data_from_button(query)['data'][2])
        answer = get_answers_as_list(question)[number_of_answer]['answer']
        if get_vote_as_dict(question.id, user, 2) is None:
            con = sqlite3.connect('db/Results_type_2.db')
            cur = con.cursor()
            cur.execute(f"""INSERT INTO Poll_{question.id}(user_id, answer_index, answer_text, date, tags)
                                    VALUES(?, ?, ?, ?, ?);""", (user.id, '', '',
                                                                datetime.datetime.now().strftime('%Y-%m-%d'),
                                                                user.tags))
            con.commit()
            con.close()

        change_vote(question, user, number_of_answer, answer)

    await query.edit_message_text(text=f"{question.text_of_question}\n" + get_text_type_2(question, user),
                                  parse_mode='HTML', reply_markup=get_reply_markup_type_2(question, user,
                                                                                          _type='get_information'))
