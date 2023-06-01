import datetime
from orm_support.db_connect import SqlAlchemyBase
import sqlalchemy


class Poll1(SqlAlchemyBase):
    __tablename__ = 'polls_type_1'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String)
    text_of_question = sqlalchemy.Column(sqlalchemy.String)
    answers = sqlalchemy.Column(sqlalchemy.String)
    author = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("authors.id"))
    border_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now() + datetime.timedelta(days=30))
    needed_tags = sqlalchemy.Column(sqlalchemy.String)
    is_active = sqlalchemy.Column(sqlalchemy.Boolean)
    additional_information = sqlalchemy.Column(sqlalchemy.String)
    balance = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    check_per_person = sqlalchemy.Column(sqlalchemy.Integer, default=20)


class Poll2(SqlAlchemyBase):
    __tablename__ = 'polls_type_2'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String)
    text_of_question = sqlalchemy.Column(sqlalchemy.String)
    answers = sqlalchemy.Column(sqlalchemy.String)
    author = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("authors.id"))
    border_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now() + datetime.timedelta(days=30))
    needed_tags = sqlalchemy.Column(sqlalchemy.String)
    is_active = sqlalchemy.Column(sqlalchemy.Boolean)
    additional_information = sqlalchemy.Column(sqlalchemy.String)
    balance = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    check_per_person = sqlalchemy.Column(sqlalchemy.Integer, default=20)


class Author(SqlAlchemyBase):
    __tablename__ = 'authors'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    telegram_id = sqlalchemy.Column(sqlalchemy.Integer)
    name = sqlalchemy.Column(sqlalchemy.String)
    surname = sqlalchemy.Column(sqlalchemy.String)
    additional_information = sqlalchemy.Column(sqlalchemy.String)
    email = sqlalchemy.Column(sqlalchemy.String)
    current_state = sqlalchemy.Column(sqlalchemy.String)
    balance = sqlalchemy.Column(sqlalchemy.Integer, default=0)


class OurUser(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    telegram_id = sqlalchemy.Column(sqlalchemy.Integer)
    name = sqlalchemy.Column(sqlalchemy.String)
    surname = sqlalchemy.Column(sqlalchemy.String)
    polls_received = sqlalchemy.Column(sqlalchemy.String)
    answered_polls = sqlalchemy.Column(sqlalchemy.String)
    additional_information = sqlalchemy.Column(sqlalchemy.String)
    tags = sqlalchemy.Column(sqlalchemy.String)
    current_state = sqlalchemy.Column(sqlalchemy.String)
    waiting_time = sqlalchemy.Column(sqlalchemy.Integer, default=5)
    next_poll_time = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now())
    balance = sqlalchemy.Column(sqlalchemy.Integer, default=0)
