# -*- coding: utf-8 -*-
# @File  : __init__.py.py
# @Author: Robinson_Jim
# @time: 18-8-1 下午7:50
from flask import Blueprint

news_blue = Blueprint("news",__name__,url_prefix="/news")

from . import views