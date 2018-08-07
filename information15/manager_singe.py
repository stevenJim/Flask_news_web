# -*- coding: utf-8 -*-
from flask import Flask
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_script import Manager
from flask_migrate import Migrate,MigrateCommand
import redis

app = Flask(__name__)

class Config(object):
    DEBUG = True

    SECRET_KEY = "rwrwirpwofjakffjaflafl"

    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@127.0.0.1:3306/information15"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_HOST = "127.0.0.1"
    REDIS_PORT =  6379

    # 设置session的存储数据类型
    SESSION_TYPE = "redis"
    # 创建一个session-redis,用来存储session
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST,port=REDIS_PORT)
    # 使用session的签名
    SESSION_USE_SIGNER = True
    # 设置session的有效期,有效期的单位是秒,86400表示一天有效
    PERMANENT_SESSION_LIFETIME = 86400 * 3

app.config.from_object(Config)

db = SQLAlchemy(app)
# 创建redis(存储验证码,存储短信验证码和图片验证码)
redis_store =  redis.StrictRedis(host=Config.REDIS_HOST,port=Config.REDIS_PORT,decode_responses=True)
# 导入session:目的用来进行持久化操作,不需要每次都让用户进行登陆,我们需要把session存储到redis当中
Session(app)
# 开启CSRF保护
CSRFProtect(app)

manager = Manager(app)
Migrate(app,db)
manager.add_command("mysql",MigrateCommand)

@app.route("/")
def index():
    return "index page2222"

if __name__ == '__main__':
    manager.run()