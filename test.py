from telegram import *
from telegram.ext import *
from random import *
import asyncio


TOKEN = '6067604242:AAEMX9qetuikGF5TexuKXPxJfjlWn6O5rsI'


async def start(update, context):
    reply_keyboard = [['/dice', '/timer']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

    await update.message.reply_text('Что хотите сделать?', reply_markup=markup)


async def dice(update, context):
    reply_keyboard = [['/one_dice', '/two_dices', '/dodecahedral_dice'], ['/come_back']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

    await update.message.reply_text('Какую кость хотите кинуть', reply_markup=markup)


async def one_dice(update, context):
    await update.message.reply_text(f'Выпало <b>{randint(1, 6)}</b>', parse_mode='HTML')


async def two_dices(update, context):
    await update.message.reply_text(f'''На первом кубике выпало <b>{randint(1, 6)}</b>
На втором кубике выпало <b>{randint(1, 6)}</b>''', parse_mode='HTML')


async def dodecahedral_dice(update, context):
    await update.message.reply_text(f'Выпало <b>{randint(1, 20)}</b>', parse_mode='HTML')


async def timer(update, context):
    reply_keyboard = [['/thirty_seconds', '/one_minute', '/five_minutes'], ['/come_back']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

    await update.message.reply_text('Таймер на какое время хотите поставить?', reply_markup=markup)


async def thirty_seconds(update, context):
    asyncio.create_task(set_timer(update, context, 30, '30 с.'))


async def one_minute(update, context):
    asyncio.create_task(set_timer(update, context, 60, '1 мин.'))


async def five_minutes(update, context):
    asyncio.create_task(set_timer(update, context, 300, '5 мин.'))


async def set_timer(update, context, time, text):
    chat_id = update.effective_message.chat_id
    remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_once(task, time, chat_id=chat_id, name=str(chat_id), data=text)
    additional_text = ''
    markup = ReplyKeyboardMarkup([['/close']], one_time_keyboard=False)
    await update.message.reply_text(f'{additional_text}Засек {text}', reply_markup=markup)


async def task(context):
    await context.bot.send_message(context.job.chat_id, text=f'{context.job.data} истекли')


def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def close(update, context):
    chat_id = update.message.chat_id
    remove_job_if_exists(str(chat_id), context)
    await update.message.reply_text('Таймер сброшен')
    asyncio.create_task(timer(update, context))


async def come_back(update, context):
    asyncio.create_task(start(update, context))


def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    application.add_handler(CommandHandler("dice", dice))
    application.add_handler(CommandHandler("one_dice", one_dice))
    application.add_handler(CommandHandler("two_dices", two_dices))
    application.add_handler(CommandHandler("dodecahedral_dice", dodecahedral_dice))
    application.add_handler(CommandHandler("come_back", come_back))

    application.add_handler(CommandHandler("timer", timer))
    application.add_handler(CommandHandler("thirty_seconds", thirty_seconds))
    application.add_handler(CommandHandler("one_minute", one_minute))
    application.add_handler(CommandHandler("five_minutes", five_minutes))
    application.add_handler(CommandHandler("close", close))

    application.run_polling()


if __name__ == '__main__':
    main()
