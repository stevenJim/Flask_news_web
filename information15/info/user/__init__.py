# -*- coding: utf-8 -*-
# @File  : __init__.py.py
# @Author: Robinson_Jim
# @time: 18-8-4 下午2:50
from flask import Blueprint

user_blue = Blueprint("user",__name__,url_prefix="/user")

from . import views