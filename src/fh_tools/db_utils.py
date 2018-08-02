#! /usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author  : MG
@Time    : 2018/4/8 21:11
@File    : db_utils.py
@contact : mmmaaaggg@163.com
@desc    : 数据库相关工具
"""
from sqlalchemy.orm.session import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import DeclarativeMeta
import json
from datetime import date, datetime, timedelta
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import Insert
from .fh_utils import date_2_str
import logging
logger = logging.getLogger()


class SessionWrapper:
    """用于对session对象进行封装，方便使用with语句进行close控制"""

    def __init__(self, session):
        self.session = session

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
        # logger.debug('db session closed')


def with_db_session(engine, expire_on_commit=True):
    """创建session对象，返回 session_wrapper 可以使用with语句进行调用"""
    db_session = sessionmaker(bind=engine, expire_on_commit=expire_on_commit)
    session = db_session()
    return SessionWrapper(session)


def get_db_session(engine, expire_on_commit=True):
    """返回 session 对象"""
    db_session = sessionmaker(bind=engine, expire_on_commit=expire_on_commit)
    session = db_session()
    return session


class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        # print("obj.__class__", obj.__class__, "isinstance(obj.__class__, DeclarativeMeta)", isinstance(obj.__class__, DeclarativeMeta))
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data)     # this will fail on non-encodable values, like other classes
                    fields[field] = data
                except TypeError:    # 添加了对datetime的处理
                    print(data)
                    if isinstance(data, datetime):
                        fields[field] = data.isoformat()
                    elif isinstance(data, date):
                        fields[field] = data.isoformat()
                    elif isinstance(data, timedelta):
                        fields[field] = (datetime.min + data).time().isoformat()
                    else:
                        fields[field] = None
            # a json-encodable dict
            return fields
        elif isinstance(obj, date):
            return json.dumps(date_2_str(obj))

        return json.JSONEncoder.default(self, obj)


@compiles(Insert)
def append_string(insert, compiler, **kw):
    """
    支持 ON DUPLICATE KEY UPDATE
    通过使用 on_duplicate_key_update=True 开启
    :param insert:
    :param compiler:
    :param kw:
    :return:
    """
    s = compiler.visit_insert(insert, **kw)
    if insert.kwargs.get('on_duplicate_key_update'):
        fields = s[s.find("(") + 1:s.find(")")].replace(" ", "").split(",")
        generated_directive = ["{0}=VALUES({0})".format(field) for field in fields]
        return s + " ON DUPLICATE KEY UPDATE " + ",".join(generated_directive)
    return s


def alter_table_2_myisam(engine_md, table_name_list=None):
    """
    修改表默认 engine 为 myisam
    :param engine_md:
    :param table_name_list:
    :return:
    """
    if table_name_list is None:
        table_name_list = engine_md.table_names()
    with with_db_session(engine=engine_md) as session:
        data_count = len(table_name_list)
        for num, table_name in enumerate(table_name_list):
            # sql_str = "show table status from {Config.DB_SCHEMA_MD} where name=:table_name"
            row_data = session.execute('show table status like :table_name', params={'table_name': table_name}).first()
            if row_data is None:
                continue
            if row_data[1].lower() == 'myisam':
                continue

            logger.info('%d/%d)修改 %s 表引擎为 MyISAM', num, data_count, table_name)
            sql_str = "ALTER TABLE %s ENGINE = MyISAM" % table_name
            session.execute(sql_str)
