from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models.comment import Comment
from models.user import User
from models.like import CommentLike

comments_bp = Blueprint("comments", __name__)

@comments_bp.route("/<path:post_slug>", methods=["GET"])
@jwt_required(optional=True)
def get_comments(post_slug):
    """获取文章所有评论（树形结构）"""
    current_user_id = None
    try:
        current_user_id = int(get_jwt_identity())
    except Exception:
        pass

    comments = (
        Comment.query
        .filter_by(post_slug=post_slug, parent_id=None, is_approved=True)
        .order_by(Comment.created_at.desc())
        .all()
    )

    result = [c.to_dict(current_user_id=current_user_id) for c in comments]
    return jsonify({"comments": result, "count": len(result)})

@comments_bp.route("/<path:post_slug>", methods=["POST"])
@jwt_required(optional=True)
def create_comment(post_slug):
    """发表评论（支持游客和登录用户）"""
    data = request.get_json() or {}
    content = data.get("content", "").strip()
    parent_id = data.get("parent_id")

    if not content:
        return jsonify({"error": "评论内容不能为空"}), 400
    if len(content) > 2000:
        return jsonify({"error": "评论不能超过 2000 字符"}), 400

    if parent_id:
        parent = Comment.query.get(parent_id)
        if not parent or parent.post_slug != post_slug:
            return jsonify({"error": "回复的评论不存在"}), 404

    # 尝试解析登录用户
    user_id = None
    try:
        user_id = int(get_jwt_identity())
    except Exception:
        pass

    # 游客评论：需要 name 和 email
    guest_name = None
    guest_email = None
    guest_qq = None
    if not user_id:
        guest_name = data.get("name", "").strip()
        guest_email = data.get("email", "").strip().lower()
        guest_qq = data.get("qq", "").strip() or None
        if not guest_name:
            return jsonify({"error": "请填写昵称"}), 400
        if len(guest_name) < 2 or len(guest_name) > 50:
            return jsonify({"error": "昵称需要 2-50 个字符"}), 400
        if not guest_email:
            return jsonify({"error": "请填写邮箱"}), 400

    comment = Comment(
        post_slug=post_slug,
        content=content,
        user_id=user_id,
        guest_name=guest_name,
        guest_email=guest_email,
        guest_qq=guest_qq,
        parent_id=parent_id,
    )
    db.session.add(comment)
    db.session.commit()

    return jsonify({"comment": comment.to_dict(current_user_id=user_id)}), 201

@comments_bp.route("/<int:comment_id>", methods=["DELETE"])
@jwt_required(optional=True)
def delete_comment(comment_id):
    """删除评论（自己的/管理员的）。游客评论无法删除"""
    comment = Comment.query.get(comment_id)

    if not comment:
        return jsonify({"error": "评论不存在"}), 404

    # 解析当前用户
    user_id = None
    try:
        user_id = int(get_jwt_identity())
    except Exception:
        pass

    # 游客评论不允许删除（没有身份验证）
    if comment.user_id is None:
        return jsonify({"error": "游客评论无法删除"}), 403

    user = User.query.get(user_id) if user_id else None
    if comment.user_id != user_id and (not user or not user.is_admin):
        return jsonify({"error": "无权删除此评论"}), 403

    # 管理员直接物理删除，普通用户软删除（标记未批准）
    if user and user.is_admin:
        db.session.delete(comment)
    else:
        comment.is_approved = False

    db.session.commit()
    return jsonify({"message": "评论已删除"})
