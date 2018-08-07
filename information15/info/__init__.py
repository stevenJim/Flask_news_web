# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask import g
from flask import render_template

from  config import Config, DevelopmentConfig, ProductionConfig, config_map
from flask_sqlalchemy import SQLAlchemy
import redis
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import generate_csrf

# 设置日志的记录等级


logging.basicConfig(level=logging.DEBUG)  # 调试debug级
# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
# 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)
# 为全局的日志工具对象（flask app使用的）添加日志记录器
logging.getLogger().addHandler(file_log_handler)

db = SQLAlchemy()
redis_store = None  # type:redis.StrictRedis


# 传进来的参数表示config的配置文件的名字
def create_app(config_name):
    app = Flask(__name__)
    # 根据字典的key,获取到字典的value
    config_class = config_map.get(config_name)

    app.config.from_object(config_class)

    db.init_app(app)
    # db = SQLAlchemy(app)
    # 创建redis(存储验证码,存储短信验证码和图片验证码)
    global redis_store
    redis_store = redis.StrictRedis(host=config_class.REDIS_HOST, port=config_class.REDIS_PORT, decode_responses=True)
    # 导入session:目的用来进行持久化操作,不需要每次都让用户进行登陆,我们需要把session存储到redis当中
    Session(app)
    # 开启CSRF保护
    CSRFProtect(app)

    # 后端生成csrf_token传给前端
    # 此方法在执行视图函数之后会调用，并且会把视图函数所产生的响应传入，可以在此方法中对响应做最后一步的统一处理
    @app.after_request
    def after_request(response):
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response

    # 注册自定义热点新闻排行榜过滤器
    from info.utils.common import index_class
    app.add_template_filter(index_class)

    # 注册首页的蓝图
    from info.index import index_blue
    app.register_blueprint(index_blue)

    # 登录注册的蓝图
    from info.passport import passport_blue
    app.register_blueprint(passport_blue)

    # 新闻详情页面蓝图
    from info.news import news_blue
    app.register_blueprint(news_blue)

    # 个人中心蓝图注册
    from info.user import user_blue
    app.register_blueprint(user_blue)

    # 注册管理员后台蓝图
    from info.admin import admin_blue
    app.register_blueprint(admin_blue)

    # 捕获404错误返回错误页面
    from info.utils.common import user_login_data
    @app.errorhandler(404)
    @app.errorhandler(405)
    @user_login_data
    def error_404_handle(error):
        user = g.user
        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template("news/404.html", data=data)

    return app
