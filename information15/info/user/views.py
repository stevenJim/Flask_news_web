# -*- coding: utf-8 -*-
# @File  : views.py
# @Author: Robinson_Jim
# @time: 18-8-4 下午2:52
from flask import abort
from flask import current_app
from flask import g, jsonify
from flask import redirect
from flask import render_template
from flask import request

from info import constants
from info.models import Category, News, User
from info.utils.image_storage import storage

from info import db
from info.utils.response_code import RET
from . import user_blue
from info.utils.common import user_login_data


@user_blue.route("/other_news_list")
@user_login_data
def other_news_list():
    page = request.args.get("p", 1)
    author_id = request.args.get("user_id")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    paginate = None
    if not author_id:
        return jsonify(errno=RET.PARAMERR, errmsg="该作者不存在")
    try:
        paginate = News.query.filter(News.user_id == author_id, News.status == 0).order_by(
            News.create_time.desc()).paginate(page, 10, False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据库失败")
    author_news = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    author_news_li = []
    for news in author_news:
        author_news_li.append(news.to_dict())

    data = {
        "news_list": author_news_li,
        "current_page": current_page,
        "total_page": total_page
    }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@user_blue.route("/other_info")
@user_login_data
def other_info():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="请登录")
    # 获取其他用户id
    author_id = request.args.get("id")
    if not author_id:
        abort(404)
    # 通过其他的id获取用户信息:
    try:
        author = User.query.get(author_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="该用户不存在")
    if not author:
        abort(404)

    is_followed = False
    if user:
        if user in author.followers:
            is_followed = True

    data = {
        "user_info": user.to_dict(),
        "other_info": author.to_dict(),
        "is_followed": is_followed
    }
    return render_template("news/other.html", data=data)


@user_blue.route("/user_follow")
@user_login_data
def user_follow():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="未登录")
    # 获取前端点击事件带来的
    page = request.args.get("p", 1)
    # 设置user_followeds/current_page/current_page有默认值:
    user_followeds = []
    current_page = 1
    current_page = 1
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    try:
        paginate = user.followed.paginate(page, 4, False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询失败")
    # 用户所有关注的作者对象:
    user_followeds = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    user_followed_li = []
    for user_followed in user_followeds:
        user_followed_li.append(user_followed.to_dict())
    data = {
        "users": user_followed_li,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("news/user_follow.html", data=data)


@user_blue.route("/news_list", )
@user_login_data
def news_list():
    user = g.user
    # 将所有的新闻分页处理
    page = request.args.get("p", 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    paginate = News.query.filter(News.user_id == user.id).paginate(page, 2, False)
    # 所有个人发布的新闻对象
    news_items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    # 用列表的形式储存每个新闻转化为字典后的新闻对象
    news_list = []
    for news_item in news_items:
        news_list.append(news_item.to_review_dict())

    data = {
        "news_list": news_list,
        "total_page": total_page, "current_page": current_page
    }

    return render_template("news/user_news_list.html", data=data)


@user_blue.route("/news_release", methods=["GET", "POST"])
@user_login_data
def news_release():
    user = g.user
    if request.method == "GET":
        # 查询所有的分类
        categories = None  # 指定查询结果为默认none,避免跑异常
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.NODATA, errmsg="数据库查询失败")

        category_list = []
        for category in categories:
            category_list.append(category.to_dict())

        # 删除默认的"最新"这个分类,这个分类是不存在的额
        category_list.pop(0)

        return render_template("news/user_news_release.html", data={"categories": category_list})
    # 当请求为post时获取前端提交的数据,存入到数据库;
    title = request.form.get("title")
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    index_image = request.files.get("index_image")
    content = request.form.get("content")

    if not all([title, category_id, digest, index_image, content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 读取图片,将图片转化为二进制
    try:
        index_image = index_image.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="图片读取失败")
    # 将图片上传到七牛云,返回值是获得图片的key,网址拼接即可拿到图片
    try:
        key = storage(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片失败")
    # 创建新闻对象往里面存入数据
    news = News()
    news.title = title
    news.source = "个人发布"
    news.digest = digest
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id
    news.user_id = user.id
    news.status = 1
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="新闻数据提交失败")
    return jsonify(errno=RET.OK, errmsg="新闻提交成功")


@user_blue.route("/collection")
@user_login_data
def collection():
    user = g.user
    # 通过前端点击获取当前页面的数字
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)

        page = 1
    # 进行分页查询
    paginate = None
    try:
        paginate = user.collection_news.paginate(page, 2, False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.NODATA, errmsg="没有收藏数据")

    collection_items = paginate.items
    # 当前页面
    current_page = paginate.page
    # 总页数
    total_page = paginate.pages
    # 将当前所有的收藏的新闻存到一个列表中
    collection_items_list = []
    for collection_item in collection_items:
        collection_items_list.append(collection_item.to_dict())

    data = {
        "total_page": total_page,
        "current_page": current_page,
        "collections": collection_items_list
    }

    return render_template("news/user_collection.html", data=data)


@user_blue.route("/pass_info", methods=["GET", "POST"])
@user_login_data
def pass_info():
    user = g.user
    # 当请求为get请求时直接展示页面
    if request.method == "GET":
        data = {
            "user_info": user.to_dict()
        }
        return render_template("news/user_pass_info.html", data=data)

    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")
    #     检验输入的旧密码和实际数据的库密码是不是一样的
    if not user.check_password(old_password):
        return jsonify(errno=RET.PARAMERR, errmsg="输入旧密码有误")
    if old_password == new_password:
        return jsonify(errno=RET.PARAMERR, errmsg="更改前后密码不能同一个")

    user.password = new_password
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="密码保存失败")

    return jsonify(errno=RET.OK, errmsg="保存成功")


@user_blue.route("/pic_info", methods=["GET", "POST"])
@user_login_data
def pic_info():
    user = g.user
    # 当请求为get请求时直接展示页面
    if request.method == "GET":
        data = {
            "user_info": user.to_dict()
        }
        return render_template("news/user_pic_info.html", data=data)
    # 读取页面上传的图片资源
    try:
        avatar_file = request.files.get("avatar").read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="图片读取失败")

    try:
        # 通过七牛云上传图片资源,storage()函数会返回一个key,用七牛云的网址加后缀key,也就是下面的url就可以获取该上传的图片
        url = storage(avatar_file)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="图片上传失败")

    # 将图片的url地址保存到对应的user的属性里,点击提交后会拼接网址到url中,
    user.avatar_url = url

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")

    return jsonify(errno=RET.OK, errmsg="图片上传成功", data={"avatar_url": constants.QINIU_DOMIN_PREFIX + url})


@user_blue.route("/base_info", methods=["GET", "POST"])
@user_login_data
def base_info():
    user = g.user
    # 当请求为get请求时直接展示页面
    if request.method == "GET":
        data = {
            "user_info": user.to_dict()
        }
        return render_template("news/user_base_info.html", data=data)

    nick_name = request.json.get("nick_name")
    signature = request.json.get("signature")
    gender = request.json.get("gender")

    if not all([nick_name, signature, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if gender not in ["MAN", "WOMAN"]:
        return jsonify(errno=RET.PARAMERR, errmsg="性别参数错误")

    user.nick_name = nick_name
    user.gender = gender
    user.signature = signature

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")

    # 将session中的签名实时更新到页面
    return jsonify(errno=RET.OK, errmsg="数据保存成功")


@user_blue.route("/info")
@user_login_data
def get_user_info():
    user = g.user
    if not user:
        return redirect("/")
    data = {
        "user_info": user.to_dict()
    }
    return render_template("news/user.html", data=data)
