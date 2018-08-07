# -*- coding: utf-8 -*-
from flask import request, jsonify
from flask import session

from info.models import User, News, Category
from info.utils.response_code import RET
from . import index_blue
from flask import render_template, current_app


@index_blue.route("/news_list")
def news_list():
    # 分类id
    cid = request.args.get("cid", 1)
    # 显示页数，默认不传的话就是第一页
    page = request.args.get("page", 1)
    # 默认一页显示多少条数据，默认传的话是10条
    per_page = request.args.get("per_page", 10)
    # paginate()方法将获取到的新闻进行分页，第一个参数是页码，第二个参数一页多少个数据，False可以防止404错误抛出
    # 如果是显示的是第一页则展示所有的新闻信息，按照创时间进行排序
    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        cid = 1
        page = 1
        per_page = 10
    """普通方法实现分类"""
    # if cid == 1:
    #     paginate = News.query.order_by(News.create_time.desc()).paginate(page, per_page, False)
    # else:
    #     paginate = News.query.filter(News.category_id == cid).order_by(News.create_time.desc()).paginate(page, per_page,
    #                                                                                   False)
    filter = [News.status == 0]
    if cid != 1:
        filter.append(News.category_id == cid)
    paginate = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page, per_page,
                                                                                     False)
    # 获取当前页面展示的数据
    items = paginate.items
    # 获取当前的页面
    current_page = paginate.page
    # 获取当前的总页数
    total_page = paginate.pages

    news_dict_li = []
    for item in items:
        news_dict_li.append(item.to_dict())

    data = {
        "news_dict_li": news_dict_li,
        "total_page": total_page,
        "current_page": current_page,
    }

    return jsonify(errno=RET.OK, errmsg="ok", data=data)


@index_blue.route("/favicon.ico")
def send_favicon():
    """显示网页图标"""
    return current_app.send_static_file('news/favicon.ico')


@index_blue.route("/")
def index():
    user_id = session.get("user_id")
    print("user_id:", user_id)
    user = None  # type:User
    if user_id:
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)
    # 从数据库中查询点击量排名前十的新闻，按照点击量的大小排名
    news = News.query.order_by(News.clicks.desc()).limit(10)
    news_list = []
    for new in news:
        news_list.append(new.to_dict())
    # 展示最新的所有分类
    categories = Category.query.all()
    category_list = []
    for category in categories:
        category_list.append(category.to_dict())

    print()
    data = {
        "user_info": user.to_dict() if user else None,
        "news_list": news_list,
        "category_list": category_list
    }

    """显示主页"""
    return render_template("news/index.html", data=data)
