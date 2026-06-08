from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app import db
from models.user import User
from models.comment import Comment
from utils.decorators import admin_required

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/comments/pending", methods=["GET"])
@jwt_required()
@admin_required
def pending_comments():
    """获取待审核评论"""
    comments = (
        Comment.query
        .filter_by(is_approved=False)
        .order_by(Comment.created_at.desc())
        .all()
    )
    return jsonify({"comments": [c.to_dict() for c in comments]})

@admin_bp.route("/comments/<int:comment_id>/approve", methods=["POST"])
@jwt_required()
@admin_required
def approve_comment(comment_id):
    """审核通过"""
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({"error": "评论不存在"}), 404
    comment.is_approved = True
    db.session.commit()
    return jsonify({"message": "审核通过"})

@admin_bp.route("/comments/<int:comment_id>/reject", methods=["POST"])
@jwt_required()
@admin_required
def reject_comment(comment_id):
    """拒绝并删除"""
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({"error": "评论不存在"}), 404
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"message": "已删除"})

@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
@admin_required
def stats():
    """统计数据"""
    from sqlalchemy import func
    return jsonify({
        "total_comments": Comment.query.count(),
        "total_users": User.query.count(),
        "total_likes": db.session.query(func.sum(Comment.likes_count)).scalar() or 0,
    })
