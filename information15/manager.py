# -*- coding: utf-8 -*-
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from info import create_app, db
from info import models
from info.models import User

"""
manager.py的作用是入口程序
"""
app = create_app("develop")

manager = Manager(app)
Migrate(app, db)
manager.add_command("mysql", MigrateCommand)

# 另外一种方式创建管理员对象
@manager.option('-n', '--name', dest='name')
@manager.option('-p', '--password', dest='password')
def create_super_user(name,password):
    user = User()
    user.mobile = name
    user.nick_name = name
    user.password = password
    user.is_admin = True

    db.session.add(user)
    db.session.commit()

if __name__ == '__main__':
    manager.run()
