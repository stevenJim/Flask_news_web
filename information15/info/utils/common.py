# -*- coding: utf-8 -*-
# @File  : common.py
# @Author: Robinson_Jim
# @time: 18-8-1 下午4:54
import functools

from flask import abort
from flask import current_app
from flask import g
from flask import session

from info.models import User


def index_class(index):
    if index == 1:
        return "first"
    elif index == 2:
        return "second"
    elif index == 3:
        return "third"


# 储存用户登录信息状态的装饰器
def user_login_data(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            user_id = session.get("user_id")
        except Exception as e:
            current_app.logger.error(e)
            abort(404)
        print("user_id:", user_id)
        user = None  # type:User
        if user_id:
            try:
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)
        # 定义一个全局的g变量储存用户的状态，任何函数需要这个状态的只要装饰了这个函数就可以使用这个变量
        g.user = user
        return func(*args, **kwargs)

    return wrapper
