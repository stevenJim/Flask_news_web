# -*- coding: utf-8 -*-
# @File  : views.py
# @Author: Robinson_Jim
# @time: 18-7-29 下午4:39
import random

import re
from datetime import datetime

from flask import current_app
from flask import make_response
from flask import request, jsonify
from flask import session

from info import constants, db
from info.lib.yuntongxun.yuntongxun.sms import CCP
from info.models import User
from info.utils.response_code import RET
from . import passport_blue
from info.utils.captcha.captcha import captcha
from info import redis_store


@passport_blue.route("/smscode", methods=["GET", "POST"])
def sms_code():
    """短信验证:
    1. 接收参数并判断是否有值
    2. 校验手机号是正确
    3. 通过传入的图片编码去redis中查询真实的图片验证码内容
    4. 进行验证码内容的比对
    5. 生成发送短信的内容并发送短信
    6. redis中保存短信验证码内容
    7. 返回发送成功的响应
    :return:
    """
    print("in-sms")
    mobile = request.json.get("mobile")
    image_code = request.json.get("image_code")
    image_code_id = request.json.get("image_code_id")
    print(mobile, image_code, image_code_id)

    # 1.接收参数并判断是否有值,有个bug不能正确的识别，当验证码
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全！")
    # 2.校验手机号是正确
    if not re.match("^1[345678][0-9]{9}$", mobile):
        return jsonify(errno=RET.DATAERR, errmsg="手机号输入有误！")
    # 3.通过传入的图片编码去redis中查询真实的图片验证码内容
    real_image_code = redis_store.get("image_code_" + image_code_id)
    # 4.确认验证码是否过期
    if real_image_code == 0:
        return jsonify(errno=RET.NODATA, errmsg="验证码过期！")
    # 5.进行验证码内容的比对,在后面加lower()全部转为小写，不区分大小写
    try:
        if real_image_code.lower() != image_code.lower():
            return jsonify(errno=RET.DATAERR, errmsg="验证码有误！")
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="验证码有误！")
    # 6.查看数据库检查收集是否被注册：
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        # 6.1 将错误记录到日志中
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg="该号码已经注册！")
    # 7.生成短信验证码，并发送短信，
    num = random.randint(0, 9999)
    random_sms_code = "%06d" % num
    # 将随机生成的6位数，存到redis中！
    redis_store.set("sms_code_" + mobile, random_sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    print("短信验证码为：", random_sms_code)
    print("短信验证的sms_code_:", "sms_code_" + mobile)
    # 发送短信：借助第三方模块--,7-31今天还没注册完成
    print(mobile, random_sms_code)
    status_code = CCP().send_template_sms("13760970891", [random_sms_code, 5], "1")
    print(status_code)
    if status_code != 0:
        return jsonify(errno=RET.THIRDERR, errmsg="短信发送失败")

    return jsonify(errno=RET.OK, errmsg="短信发送成功")


@passport_blue.route("/image_code")
def image_code():
    """验证码验证"""
    code_id = request.args.get("code_id")
    print("code_id:", code_id)

    name, text, image = captcha.captcha.generate_captcha()
    # 这里需要再redis_store对象初始化的时候进行，decode_response=true，存入时候进行解码传入
    redis_store.set("image_code_" + code_id, text, constants.SMS_CODE_REDIS_EXPIRES)
    print("图片验证码内容：", text)

    resp = make_response(image)
    resp.headers["Content-Type"] = "image/jpg"

    return resp


@passport_blue.route("/register", methods=["GET", "POST"])
def register():
    """注册页面"""
    """
    1. 获取参数和判断是否有值
    2. 从redis中获取指定手机号对应的短信验证码的
    3. 校验验证码
    4. 初始化 user 模型，并设置数据并添加到数据库
    5. 保存当前用户的状态
    6. 返回注册的结果
    :return:
    """
    print("in-register")
    mobile = request.json.get("mobile")
    smscode = request.json.get("smscode")
    password = request.json.get("password")
    print(mobile, smscode, password)
    # 1.获取参数和判断是否有值
    if not all([mobile, smscode, smscode]):
        return jsonify(errno=RET.PARAMERR, errmsg="缺少正确的参数")
    # 2.从redis中获取指定手机号对应的短信验证码的

    try:
        real_sms_code = redis_store.get("sms_code_" + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.NODATA, errmsg="短信验证码已经过期")
    # 3.校验验证码
    print(real_sms_code)
    print(smscode)
    if real_sms_code != smscode:
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码有误")
    # 4.初始化 user 模型，并设置数据并添加到数据库
    # 5.保存当前用户的状态
    # 创建一个用户对象，用来注册用户
    user = User()
    user.mobile = mobile
    user.password = password
    user.nick_name = mobile
    # 获取当前时间来注册，
    user.last_login = datetime.now()
    db.session.add(user)
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="注册成功")


@passport_blue.route("/login", methods=["GET", "POST"])
def login():
    """处理登录界面"""
    """
    1. 获取参数和判断是否有值
    2. 从数据库查询出指定的用户
    3. 校验密码
    4. 保存用户登录状态
    5. 返回结果
    :return:
    """
    print("in--login")
    mobile = request.json.get("mobile")
    password = request.json.get("password")
    print(mobile, password)
    # 1/获取参数和判断是否有值
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="请输入完整的参数")
    # 2/从数据库查询出指定的用户
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
    if not user:
        return jsonify(errno=RET.NODATA, errmsg="该账号未注册")
    # 3/校验密码
    if not user.check_password(password):
        return jsonify(errno=RET.DATAERR, errmsg="请输入正确的密码")
    # 4/保存用户登录状态.跟网易新闻一样，用session进行实现，用户信息保存到session
    session["user_id"] = user.id

    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    user.last_login = datetime.now()

    return jsonify(errno=RET.OK, errmsg="登录成功")


@passport_blue.route("/logout", methods=["GET", "POST"])
def logout():
    """登出"""
    session.pop("user_id", None)
    session.pop("nick_name", None)
    session.pop("mobile", None)
    # session.pop('user_id', None)
    # session.pop('nick_name', None)
    # session.pop('mobile', None)
    session.pop('is_admin', None)

    return jsonify(errno=RET.OK, errmsg="退出登录成功")
