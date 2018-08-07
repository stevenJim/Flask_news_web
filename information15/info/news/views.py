# -*- coding: utf-8 -*-
# @File  : views.py
# @Author: Robinson_Jim
# @time: 18-8-1 下午7:51
from flask import abort, jsonify
from flask import current_app
from flask import g
from flask import render_template
from flask import request

from info import db
from info.models import News, Comment, CommentLike, User
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import news_blue


@news_blue.route("/followed_user", methods=["POST"])
@user_login_data
def followed_user():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 从前端获取user_id和点击动作:
    author_id = request.json.get("user_id")
    action = request.json.get("action")
    try:
        author = User.query.get(author_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询失败")

    if action not in ["follow", "unfollow"]:
        return jsonify(errno=RET.PARAMERR, errmsg="关注失败")
    # 该文章的作者在登录用户的关注里面，就显示已经关注，如果不在就显示未关注：
    if action == "follow":
        if user in author.followers:
            return jsonify(errno=RET.PARAMERR, errmsg="已经关注")
        author.followers.append(user)

    else:
        if user not in author.followers:
            return jsonify(errno=RET.PARAMERR, errmsg="未关注")
        author.followers.remove(user)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")

    return jsonify(errno=RET.OK, errmsg="OK")


@news_blue.route("/comment_like", methods=["POST", "GET"])
@user_login_data
def comment_like():
    """点赞"""

    if not g.user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 获取前端传来的数据
    comment_id = request.json.get("comment_id")
    news_id = request.json.get("news_id")
    action = request.json.get("action")
    # 判断参数
    if not all([comment_id, news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ["add", "remove"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询评论数据
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="评论数据不存在")

    commentLike = CommentLike.query.filter_by(comment_id=comment_id, user_id=g.user.id).first()
    if action == "add":
        if not commentLike:
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = g.user.id
            db.session.add(comment_like)
            comment.like_count += 1
    else:
        if commentLike:
            db.session.delete(commentLike)
            comment.like_count -= 1

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="操作失败")

    return jsonify(errno=RET.OK, errmsg="操作成功")


@news_blue.route("/news_comment", methods=["POST", "GET"])
@user_login_data
def news_comment():
    """新闻评论"""

    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    news_id = request.json.get("news_id")
    comment_str = request.json.get("comment")
    parent_id = request.json.get("parent_id")
    # 如果没有新闻和评论不允许提交到数据库
    if not all([news_id, comment_str]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 通过新闻news_id查询新闻
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻数据不存在")

    # 初始化评论模型,保存评论数据:
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news.id
    comment.content = comment_str
    if parent_id:
        comment.parent_id = parent_id

    # 保存到数据库
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="评论提交到数据库错误")

    return jsonify(errno=RET.OK, errmsg="评论成功", data=comment.to_dict())


@news_blue.route("/news_collect", methods=["POST", "GET"])
@user_login_data
def news_collect():
    """新闻收藏"""
    print("in--collect")
    # 新闻id是必须要传过来的，不然不知道是收藏的那个新闻
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    # 如果用户不存在就返回需要用户登录
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 如果新闻不存在就提示用户该新闻不存在
    if not news_id:
        return jsonify(errno=RET.NODATA, errmsg="该新闻不存在")
    # 如果用户输入的数据不是：["collect","cancel_collect"]中的一个报错
    if action not in ["collect", "cancel_collect"]:
        return jsonify(errno=RET.PARAMERR, errmsg="收藏失败")

    # 查询新闻对象
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻数据失败")
    # 如果新闻不存在，就返回
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="该新闻不存在")
    # 判断用户行为:
    if action == "collect":
        # 用户与新闻是一个一堆多的关心,通过model.py可以找到 user中有个关于News的属性,就可以找到该用户收藏的所有新闻列表,然后网列表中添加这条新闻对象
        user.collection_news.append(news)
    else:
        user.collection_news.remove(news)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="新闻收藏失败")

    return jsonify(errno=RET.OK, errmsg="收藏成功")


@news_blue.route("/<int:news_id>")
@user_login_data
def news_detail(news_id):
    """新闻页展示"""
    # 获取登录状态信息
    user = g.user
    # 从数据库中查询点击量排名前十的新闻，按照点击量的大小排名
    news = News.query.order_by(News.clicks.desc()).limit(10)
    news_list = []
    for new in news:
        news_list.append(new.to_dict())

    # 根据news_id查询出来对应的新闻对象
    try:
        news = News.query.get(news_id)

    except Exception as e:
        current_app.logger.error(e)
        abort(404)
    if not news:
        abort(404)

    news.clicks += 1
    print(user)

    # 保持新闻是否被收藏状态,网页默认进入是没有收藏的,通过查询展示是否被收藏然后展示
    is_collected = False  # 保存的收藏的状态
    is_followed = False
    if user:
        if news in user.collection_news:
            is_collected = True
            #    获取当前新闻的作者:
        # author = news.user
        author = User.query.filter(User.id == news.user_id).first()
        if author in user.followed:
            is_followed = True

    print(is_collected)
    print(is_followed)

    """
    展示评论列表
    """
    try:
        comment = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="查询数据错误")

    comment_likes_ids = []
    comment_list = []
    if user:
        # 获取当前用户所有的点赞
        comment_likes = CommentLike.query.filter(CommentLike.user_id == user.id).all()
        # 获取当前用户每条点赞的评论id
        comment_likes_ids = [comment_like.comment_id for comment_like in comment_likes]

    for item in comment:
        # 获取每条评论
        comment_item = item.to_dict()
        # 默认该用户没有给评论点赞
        comment_item["is_like"] = False
        if item.id in comment_likes_ids:
            # 当当前评论的id在用户的所有评论id中,说明该条评论用户点赞了!
            comment_item["is_like"] = True
        comment_list.append(comment_item)

    db.session.add(news)
    db.session.commit()
    news = news.to_dict()
    data = {
        "user_info": user.to_dict() if user else None,
        "news_list": news_list,
        "news": news,
        "is_collected": is_collected,
        "comments": comment_list,
        "is_followed": is_followed
    }

    return render_template("news/detail.html", data=data)
