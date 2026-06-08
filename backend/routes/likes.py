from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models.comment import Comment
from models.like import CommentLike

likes_bp = Blueprint("likes", __name__)

@likes_bp.route("/<int:comment_id>/toggle", methods=["POST"])
@jwt_required()
def toggle_like(comment_id):
    """点赞 / 取消点赞"""
    user_id = int(get_jwt_identity())
    comment = Comment.query.get(comment_id)

    if not comment:
        return jsonify({"error": "评论不存在"}), 404

    existing = CommentLike.query.filter_by(
        user_id=user_id, comment_id=comment_id
    ).first()

    if existing:
        db.session.delete(existing)
        comment.likes_count = max(0, comment.likes_count - 1)
        db.session.commit()
        return jsonify({"liked": False, "likes_count": comment.likes_count})
    else:
        like = CommentLike(user_id=user_id, comment_id=comment_id)
        db.session.add(like)
        comment.likes_count += 1
        db.session.commit()
        return jsonify({"liked": True, "likes_count": comment.likes_count})
