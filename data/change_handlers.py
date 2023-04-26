from data.base import *
from telegram import *
from telegram.ext import *


async def append_tags(update, person):
    sorted_tags = sort_tags(update.message.text.replace(' ', ''))

    new_tags, old_tags = [], []
    if person.tags:
        for tag in sorted_tags['correct_tags']:
            if tag not in person.tags.split(','):
                new_tags.append(tag)
            else:
                old_tags.append(tag)

    else:
        new_tags = sorted_tags['correct_tags']

    if person.tags:
        person.tags = ','.join(person.tags.split(',') + new_tags)
    else:
        person.tags = ','.join(new_tags)

    db_sess.commit()

    text = ''
    if sorted_tags['invalid_tags']:
        text += f'Теги {", ".join(sorted_tags["invalid_tags"])} не существуют\n'
    if old_tags:
        text += f'Теги {", ".join(old_tags)} уже были записаны\n'
    if new_tags:
        text += f'Записаны теги {", ".join(new_tags)}'

    return await update.message.reply_text(text=text)


async def remove_tags(update, person):
    if update.message.text == 'None':
        return await update.message.reply_text(text='Ни один тег не был удален')

    sorted_tags = sort_tags(update.message.text.replace(' ', ''))
    new_tags, old_tags = [], []
    if person.tags:
        for tag in sorted_tags['correct_tags']:
            if tag not in person.tags.split(','):
                new_tags.append(tag)
            else:
                old_tags.append(tag)

    else:
        new_tags = sorted_tags['correct_tags']

    if person.tags:
        person.tags = ','.join(list(set(person.tags.split(',')) - set(old_tags)))
    else:
        return await update.message.reply_text(text='Ни один тег не удален')

    db_sess.commit()

    text = ''

    if sorted_tags['invalid_tags']:
        text += f'Теги {", ".join(sorted_tags["invalid_tags"])} не существуют\n'
    if new_tags:
        text += f'Теги {", ".join(new_tags)} не были записаны и раньше\n'
    if old_tags:
        text += f'Удалены теги {", ".join(old_tags)}'

    return await update.message.reply_text(text=text)


async def append_answer(update, question):
    if question.answers:
        if update.message.text in list(map(lambda x: x.split(':')[0], question.answers.split('|'))):
            return await update.message.reply_text(text=f'Вариант ответа <i><b>{update.message.text}</b></i>'
                                                        f' уже существует')

        question.answers = '|'.join(question.answers.split('|') + [f'{update.message.text}:0'])
    else:
        question.answers = f'{update.message.text}:0'
    db_sess.commit()
    return await update.message.reply_text(text=f'Записан новый вариант ответа {update.message.text}')


async def delete_answer(update, question):
    try:
        answer_id = int(update.message.text) - 1
        if answer_id < 0:
            raise IndexError

        if question.answers:
            answers = get_answers_as_list(question)
            answers.pop(answer_id)
            question.answers = '|'.join(list(map(lambda x: f'{x["answer"]}:0', answers)))
            db_sess.commit()

        return await update.message.reply_text(text=f'Вариант ответа был удален')

    except ValueError:
        return await update.message.reply_text(text=f'Вы введи данные в неккоректном формате,'
                                                    f' неободимо было ввести целое число')
    except IndexError:
        return await update.message.reply_text(text=f'Вы ввели неккоректный индекс ответа,'
                                                    f' ответа с таким индексом не существует')


async def change_name(update, person):
    person.name = update.message.text
    db_sess.commit()
    return await update.message.reply_text(text=f'Ваше имя изменено на <i><b>{person.name}</b></i>',
                                           parse_mode='HTML')


async def change_surname(update, person):
    person.surname = update.message.text
    db_sess.commit()
    return await update.message.reply_text(text=f'Ваша фамилия изменена на <i><b>{person.surname}</b></i>',
                                           parse_mode='HTML')


async def change_additional_information(update, person):
    person.additional_information = update.message.text
    db_sess.commit()
    return await update.message.reply_text(text=f'Дополнительная информация изменена'
                                                f' на <i><b>{person.additional_information}</b></i>',
                                           parse_mode='HTML')


async def change_email(update, person):
    person.email = update.message.text
    db_sess.commit()
    return await update.message.reply_text(text=f'Ваш email изменен на <i><b>{person.email}</b></i>',
                                           parse_mode='HTML')


async def change_title(update, question):
    question.title = update.message.text
    db_sess.commit()
    return await update.message.reply_text(text=f'Название изменено на <i><b>{question.title}</b></i>',
                                           parse_mode='HTML')


async def change_text(update, question):
    question.text_of_question = update.message.text
    db_sess.commit()
    return await update.message.reply_text(text=f'Текст изменен на <i><b>{question.text_of_question}</b></i>',
                                           parse_mode='HTML')


async def change_needed_tags(update, question):
    if update.message.text == 'None':
        question.needed_tags = ''
        db_sess.commit()
        return await update.message.reply_text(text='Теги не были выбраны')

    sorted_tags = sort_tags(update.message.text.replace(' ', ''))
    question.needed_tags = ','.join(sorted_tags['correct_tags'])
    db_sess.commit()
    text_of_mes = ''

    if sorted_tags['invalid_tags']:
        text_of_mes += f'Теги {", ".join(sorted_tags["invalid_tags"])} не существуют\n'

    return await update.message.reply_text(text=text_of_mes + f'Записаны теги'
                                                              f' {", ".join(sorted_tags["correct_tags"])}')


async def change_tags(update, person):
    sorted_tags = sort_tags(update.message.text.replace(' ', ''))
    person.tags = ','.join(sorted_tags['correct_tags'])
    db_sess.commit()
    text_of_mes = ''

    if sorted_tags['invalid_tags']:
        text_of_mes += f'Теги {", ".join(sorted_tags["invalid_tags"])} не существуют\n'

    return await update.message.reply_text(text=text_of_mes + f'Записаны только теги'
                                                              f' {", ".join(sorted_tags["correct_tags"])}')


async def change_waiting_time(update, person):
    try:
        person.waiting_time = float(update.message.text)
        db_sess.commit()
        return await update.message.reply_text(text=f'Время между опросами изменено'
                                                    f' на <i><b>{person.waiting_time}</b></i>',
                                               parse_mode='HTML')
    except ValueError:
        mes = await update.message.reply_text(text=f'Вы ввели данные в неверном формате, нужно ввести'
                                                   f' только неотрицательное вещественное число минут')
        mes_2 = await update.message.reply_text(text='Введите время, которое будет проходить между'
                                                     ' отправками опросов вам')
        change_state_characteristic(person, 'mes_to_delete',
                                    ','.join(get_state(person)['mes_to_delete'].split(',') + [str(
                                        mes.message_id)] + [str(mes_2.message_id)]))
        return mes


async def get_results_by_tags(update, question):
    sorted_tags = sort_tags(update.message.text.replace(' ', ''))
    text_of_mes = ''

    if sorted_tags['invalid_tags']:
        text_of_mes += f'Теги {", ".join(sorted_tags["invalid_tags"])} не существуют\n'

        await update.message.reply_text(text=text_of_mes)

    results = ''
    all_votes = get_all_votes_with_tags(question.id, sorted_tags['correct_tags'])
    number_of_votes = len(all_votes)

    if number_of_votes == 0:
        return await update.message.reply_text(text=f'Нет ни одного голоса от человека с такими тегами')

    else:
        for answer in list(map(lambda x: x['answer'], get_answers_as_list(question))):
            number_of_votes_answer = len(list(filter(lambda x: x["answer_text"] == answer, all_votes)))
            results += f'    {answer}:' \
                       f' {round(number_of_votes_answer / number_of_votes * 100, 2)}%\n'

        return await update.message.reply_text(text=f'Results of people with'
                                                    f' tags {", ".join(sorted_tags["correct_tags"])}:\n' + results)


async def invalid_text(update, person):
    return await update.message.reply_text(text=f'Мяу')


async def callback_change_name(query, person):
    change_state_characteristic(person, 'current_state', 'changing_name')
    return await query.message.reply_text(text='Введите свое имя')


async def callback_change_surname(query, person):
    change_state_characteristic(person, 'current_state', 'changing_surname')
    return await query.message.reply_text(text='Введите свою фамилию')


async def callback_change_title(query, person):
    change_state_characteristic(person, 'current_state', 'changing_title')
    return await query.message.reply_text(text='Введите название опроса')


async def callback_change_text(query, person):
    change_state_characteristic(person, 'current_state', 'changing_text')
    return await query.message.reply_text(text='Введите текст опроса')


async def callback_change_additional_information(query, person):
    change_state_characteristic(person, 'current_state', 'changing_additional_information')
    return await query.message.reply_text(text='Введите дополнительную иинформацию')


async def callback_change_email(query, person):
    change_state_characteristic(person, 'current_state', 'changing_email')
    return await query.message.reply_text(text='Введите свой email')


async def callback_change_waiting_time(query, person):
    change_state_characteristic(person, 'current_state', 'changing_waiting_time')
    return await query.message.reply_text(text='Введите время, через которое вам будут присылаться опросы')


async def callback_change_needed_tags(query, person):
    bot = Bot(TOKEN)
    if type(person) == Author:
        bot = Bot(TOKEN_FOR_BUSINESSMEN)
    change_state_characteristic(person, 'current_state', 'changing_needed_tags')
    mes = await query.message.reply_text(text='Просмотрите файл и введите все качества, которые подходят к людям,'
                                              ' на которых нацелен опрос (Если вы не хотите выбирать теги, введите'
                                              ' "None")')
    mes_file = await bot.send_document(query.message.chat_id, open(file_gen(), 'r'))
    change_state_characteristic(person, 'mes_to_delete', f"{mes_file.message_id}")
    return mes


async def callback_change_tags(query, person):
    bot = Bot(TOKEN)
    if type(person) == Author:
        bot = Bot(TOKEN_FOR_BUSINESSMEN)
    change_state_characteristic(person, 'current_state', 'changing_tags')
    mes = await query.message.reply_text(text='Просмотрите файл и введите все качества, которые к вам'
                                              ' (Если вы не хотите выбирать теги, введите'
                                              ' "None")')
    mes_file = await bot.send_document(query.message.chat_id, open(file_gen(), 'r'))
    change_state_characteristic(person, 'mes_to_delete', f"{mes_file.message_id}")
    return mes


async def callback_append_tags(query, person):
    change_state_characteristic(person, 'current_state', 'appending_tags')
    bot = Bot(TOKEN)
    mes = await query.message.reply_text(text='Просмотрите файл и введите все качества, которые подходят к вам')
    mes_file = await bot.send_document(query.message.chat_id, open(file_gen(), 'r'))
    append_mes_to_delete(person, mes_file)
    return mes


async def callback_delete_tags(query, person):
    # if not person.tags:
    #     return await query.message.reply_text(text='У
    #     вас нет ни одного тега, следовательно ни один тег нельзя удалить')

    change_state_characteristic(person, 'current_state', 'removing_tags')
    return await query.message.reply_text(text=f'Просмотрите ваши теги и напишите те, которые хотите удалить\n'
                                               f'Ваши теги: {person.tags}')


async def callback_get_results_by_tags(query, person):
    change_state_characteristic(person, 'current_state', 'getting_results_by_tags')
    bot = Bot(TOKEN_FOR_BUSINESSMEN)
    mes = await query.message.reply_text(text='Просмотрите файл и введите все качества, которые подходят к людям,'
                                              ' ответы которых вы хотите посмотреть')
    mes_file = await bot.send_document(query.message.chat_id, open(file_gen(), 'r'))
    append_mes_to_delete(person, mes_file)
    return mes


async def callback_append_answer(query, person):
    change_state_characteristic(person, 'current_state', 'appending_answer')
    return await query.message.reply_text(text='Введите новый вариант ответа')


async def callback_delete_answer(query, person):
    change_state_characteristic(person, 'current_state', 'removing_answer')
    return await query.message.reply_text(text='Введите порядковый номер ответа, который хотите удалить')
