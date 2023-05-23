from data.base import TOKEN, TOKEN_FOR_BUSINESSMEN, db_sess, get_state
from data.businessmen_data.working_with_data import *
from telegram import Bot
from flask import Flask, request
from orm_support.db_connect import *
from orm_support.all_db_models import *
import asyncio


app = Flask(__name__)


def check_if_successful_payment(request):
    try:
        if request.json["event"] == "payment.succeeded":
            return True
    except KeyError:
        return False

    return False


@app.route('/', methods=["POST"])
def process():
    if check_if_successful_payment(request):
        chat_id = int(request.json["object"]["metadata"]["chat_id"])
        bot = Bot(TOKEN)
        person = None
        if request.json["object"]["metadata"]["user"] == "true":
            user = db_sess.query(OurUser).filter(OurUser.telegram_id == chat_id)
            user.balance += int(float(request.json["object"]["amount"]["value"]))
            db_sess.commit()
            person = user
        if request.json["object"]["metadata"]["author"] == "true":
            bot = Bot(TOKEN_FOR_BUSINESSMEN)
            author = db_sess.query(Author).filter(Author.telegram_id == chat_id).first()
            author.balance += int(float(request.json["object"]["amount"]["value"]))
            db_sess.commit()
            person = author
        message_id = int(request.json["object"]["metadata"]["message"])
        asyncio.run(send_mes(chat_id, message_id, bot, int(float(request.json["object"]["amount"]["value"]))))

    return {"ok": True}


async def send_mes(chat_id, message_id, bot, amount):
    await bot.editMessageText(f"Оплата прошла успешно, ваш баланс пополнен на {amount} рублей",
                              chat_id=chat_id, message_id=message_id)


app.run(port=5050, host='127.0.0.1')
