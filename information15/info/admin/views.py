# -*- coding: utf-8 -*-
# @File  : views.py
# @Author: Robinson_Jim
# @time: 18-8-4 下午9:44
import time
from datetime import datetime, timedelta

from flask import current_app
from flask import g
from flask import redirect
from flask import render_template, jsonify
from flask import request
from flask import session
from flask import url_for

from info import constants
from info import db
from info.utils.common import user_login_data

from info.models import User, News, Category
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import admin_blue


@admin_blue.route("/add_category", methods=["POST", "GET"])
def add_category():
    category_id = request.json.get("id")
    category_name = request.json.get("name")

    #     不允许添加或者修改的结果空值:
    if not category_name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if category_id:
        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
        category.name = category_name
    else:
        category = Category()
        category.name = category_name
        db.session.add(category)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    return jsonify(errno=RET.OK, errmsg="ok")


@admin_blue.route("/news_type", methods=["POST", "GET"])
def news_category():
    """查询展示分类信息"""
    categories = Category.query.all()
    category_li = []
    for category in categories:
        category_li.append(category.to_dict())
    # 删除最新的分类
    category_li.pop(0)
    data = {
        "categories": category_li
    }
    return render_template("admin/news_type.html", data=data)


@admin_blue.route("/news_edit_detail", methods=["POST", "GET"])
def news_edit_detail():
    if request.method == "GET":
        try:
            news_id = request.args.get("news_id")
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="获取新闻id失败")

        if not news_id:
            return render_template("admin/news_edit.html", data={"errmsg": "该新闻不存在"})

        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_edit.html", data={"errmsg": "该新闻不存在"})

        if not news:
            return render_template("admin/news_edit.html", data={"errmsg": "该新闻不存在"})

        # 查询分类数据:
        categories = Category.query.all()
        category_li = []
        for category in categories:
            category_dict = category.to_dict()
            # 进行筛选不然每次进入编辑页面都是显示的是,股市这个第一个分类.应该是准确的指向当前文章的分类,增加一个字段就可以了!
            category_dict["is_selected"] = False
            if category.id == news.category_id:
                category_dict["is_selected"] = True

            category_li.append(category_dict)

        # 其中最新这条不是分类需要移除
        category_li.pop(0)
        data = {
            "news": news.to_dict(),
            "categories": category_li

        }
        return render_template("admin/news_edit_detail.html", data=data)

    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    # 1.1 判断数据是否有值
    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")
    if index_image:
        try:
            index_image = index_image.read()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="参数有误")
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    # 2. 将标题图片上传到七牛
    try:
        key = storage(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    # 3. 设置相关数据
    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id

    # 4. 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    # 5. 返回结果
    return jsonify(errno=RET.OK, errmsg="编辑成功")


@admin_blue.route("/news_edit")
def news_edit():
    page = request.args.get("p", 1)
    # 搜索关键字
    keywords = request.args.get("keywords", "")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    current_page = 1
    total_page = 1
    # 添加多种过滤器
    filters = [News.status == 0]
    if keywords:
        filters.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, 10, False)
        news_items = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_list = []
    for news in news_items:
        news_list.append(news.to_dict())
    data = {
        "current_page": current_page,
        "total_page": total_page,
        "news_list": news_list
    }

    return render_template("admin/news_edit.html", data=data)


@admin_blue.route("/news_review_detail", methods=["GET", "POST"])
def news_review_detail():
    """新闻详情审核"""
    if request.method == "GET":
        #     获取前端传来的新闻id
        news_id = request.args.get("news_id")
        if not news_id:
            return render_template("admin/news_review.html", data={"errno": "RET.PARAMERR", "errmsg": "该新闻不存在"})
        # 通过新闻id找到对应的新闻
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_review.html", data={"errno": "RET.PARAMERR", "errmsg": "该新闻不存在"})

        if not news:
            return render_template("admin/news_review.html", data={"errno": RET.PARAMERR, "errmsg": "该新闻不存在"})

        # 返回数据给前端
        return render_template("admin/news_review_detail.html", data={"news": news.to_dict()})
    # 提交修改文件
    news_id = request.json.get("news_id")
    action = request.json.get("action")
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ["accept", "reject"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    news = None  # type:News
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 根据不同的状态传入不同的值:
    if action == "accept":
        news.status = 0
    else:
        # 拒绝的原因:
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="未通过原因不能为空")

        news.status = -1
        news.reason = reason
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据库保存失败")
    return jsonify(errno=RET.OK, errmsg="操作成功")


@admin_blue.route("/news_review")
def news_review():
    """获取所有用户列表"""
    page = request.args.get("p", 1)
    # 加入搜索关键字功能
    keywords = request.args.get("keywords", "")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    current_page = 1
    total_page = 1
    # 添加多种过滤器
    filters = [News.status != 0]
    if keywords:
        filters.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, 10, False)
        news_items = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_list = []
    for news in news_items:
        news_list.append(news.to_review_dict())
    data = {
        "current_page": current_page,
        "total_page": total_page,
        "news_list": news_list
    }
    return render_template("admin/news_review.html", data=data)


@admin_blue.route("/user_list")
def user_list():
    """获取所有用户列表"""
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    current_page = 1
    total_page = 1
    try:
        paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc()).paginate(page, 10, False)
        user_items = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    users_list = []
    for user_item in user_items:
        users_list.append(user_item.to_admin_dict())
    data = {
        "current_page": current_page,
        "total_page": total_page,
        "users": users_list
    }
    return render_template("admin/user_list.html", data=data)


@admin_blue.route("/logout")
def admin_logout():
    """
    清除session中保存的信息:
    :return:
    """
    session.pop("user_id")
    session.pop("nick_name")
    session.pop("mobile")
    session.pop("is_admin")

    return redirect(url_for("admin.admin_login"))


@admin_blue.route("/user_count")
def user_count():
    # 非管理员人数
    total_count = 0
    try:
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)
    now = time.localtime()
    #     用户这个月新增人数
    mon_count = 0
    try:

        # 获取本月格式化的时间
        mon_begin = "%d-%02d-01" % (now.tm_year, now.tm_mon)
        mon_begin_date = datetime.strptime(mon_begin, "%Y-%m-%d")
        mon_count = User.query.filter(User.is_admin == False, User.create_time >= mon_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)
    # 当天增加的人数:
    day_count = 0
    try:
        day_begin = '%d-%02d-%02d' % (now.tm_year, now.tm_mon, now.tm_mday)
        day_begin_date = datetime.strptime(day_begin, '%Y-%m-%d')
        day_count = User.query.filter(User.is_admin == False, User.create_time > day_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)
    # 获取图表需要的信息:
    # 用两个列表分别存储用户每天活跃的人数,另外是储存每天的时间:
    active_count = []
    active_time = []
    # 获取当天的00:00:00
    now = time.localtime()
    today_begin = '%d-%02d-%02d' % (now.tm_year, now.tm_mon, now.tm_mday)
    today_begin_date = datetime.strptime(today_begin, '%Y-%m-%d')
    # 依次从当天算起算到后面30天的数据:
    for i in range(31):
        begin_date = today_begin_date - timedelta(days=i)
        end_date = today_begin_date - timedelta(days=i - 1)
        # 获得今天的人数
        count = 0
        try:
            count = User.query.filter(User.is_admin == False, User.last_login > begin_date,
                                      User.last_login < end_date).count()
        except Exception as e:
            current_app.logger.error(e)
        active_count.append(count)
        # 获取今天的日期:begin_date获取的时间是有格式的如:2018-08-04:00:00:00
        active_time.append(begin_date.strftime('%Y-%m-%d'))
    # 需要将两个表进行反转,才可以得到时间由小到大的数据:
    active_time.reverse()
    active_count.reverse()

    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": day_count,
        "active_count": active_count,
        "active_time": active_time
    }

    return render_template("admin/user_count.html", data=data)


@admin_blue.route("/index")
@user_login_data
def admin_index():
    # TODO 不是管理员也能进入后台,需要解决,使用的是在每次视图函数请求前,进行身份验证
    user = g.user
    # user_id = session.get("user_id", None)
    is_admin = session.get("is_admin", False)
    # if not user_id and not is_admin:
    if not is_admin:
        return redirect(url_for("admin.admin_login"))
    return render_template("admin/index.html", user=user.to_dict() if user else None)


@admin_blue.route("/login", methods=["POST", "GET"])
def admin_login():
    if request.method == "GET":
        user_id = session.get("user_id")
        is_admin = session.get("is_admin")
        if user_id and is_admin:
            return redirect(url_for("admin.admin_index"))
        return render_template("admin/login.html")
    # 取得管理输入的用户名和密码:
    username = request.form.get("username")
    password = request.form.get("password")

    if not all([username, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="请输入完整的数据")

    try:
        user = User.query.filter(User.mobile == username).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template("admin/login.html", errmsg="数据库查询错误")
    if not user:
        return render_template("admin/login.html", errmsg="该用户不是管理员")
    if not user.check_password(password):
        return render_template("admin/login.html", errmsg="密码错误")
    if not user.is_admin:
        return render_template("admin/login.html", errmsg="该用户没有管理员权限")

    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["is_admin"] = user.is_admin

    return redirect(url_for("admin.admin_index"))
