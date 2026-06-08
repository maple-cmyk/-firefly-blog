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
@jwt_required()
def create_comment(post_slug):
    """发表评论"""
    user_id = int(get_jwt_identity())
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

    comment = Comment(
        post_slug=post_slug,
        content=content,
        user_id=user_id,
        parent_id=parent_id,
    )
    db.session.add(comment)
    db.session.commit()

    return jsonify({"comment": comment.to_dict(current_user_id=user_id)}), 201

@comments_bp.route("/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def delete_comment(comment_id):
    """删除评论（自己的/管理员的）"""
    user_id = int(get_jwt_identity())
    comment = Comment.query.get(comment_id)

    if not comment:
        return jsonify({"error": "评论不存在"}), 404

    user = User.query.get(user_id)
    if comment.user_id != user_id and (not user or not user.is_admin):
        return jsonify({"error": "无权删除此评论"}), 403

    # 管理员直接物理删除，普通用户软删除（标记未批准）
    if user and user.is_admin:
        db.session.delete(comment)
    else:
        comment.is_approved = False

    db.session.commit()
    return jsonify({"message": "评论已删除"})
