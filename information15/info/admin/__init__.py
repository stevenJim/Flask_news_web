# -*- coding: utf-8 -*-
# @File  : __init__.py.py
# @Author: Robinson_Jim
# @time: 18-8-4 下午9:42

from flask import Blueprint
from flask import redirect
from flask import request
from flask import session
from flask import url_for

admin_blue = Blueprint("admin", __name__, url_prefix="/admin")

from . import views


# 进行后台的身份验证:不是管理员不允许直接进入后台主页!!!
@admin_blue.before_request
def admin_check():
    # 如果session中的没有user_id和is_admin,表明不是管理员,另外不允许任何人直接访问以"admin/index"的后台主页,只能是直接跳转过去!
    # user_id = session.get("user_id")
    is_admin = session.get("is_admin", False)
    if not is_admin and request.url.endswith("admin/index"):
        return redirect("/")
