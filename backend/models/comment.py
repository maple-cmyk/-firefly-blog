from datetime import datetime, timezone
from app import db

class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    post_slug = db.Column(db.String(500), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    guest_name = db.Column(db.String(50), nullable=True)
    guest_email = db.Column(db.String(120), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)
    likes_count = db.Column(db.Integer, default=0)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    replies = db.relationship(
        "Comment",
        backref=db.backref("parent", remote_side=[id]),
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_user=True, current_user_id=None):
        data = {
            "id": self.id,
            "post_slug": self.post_slug,
            "content": self.content,
            "parent_id": self.parent_id,
            "likes_count": self.likes_count,
            "is_approved": self.is_approved,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        # 只对顶层评论包含嵌套回复
        if not self.parent_id:
            data["replies"] = [
                r.to_dict(include_user=include_user, current_user_id=current_user_id)
                for r in self.replies.order_by(Comment.created_at.asc()).all()
            ]
        else:
            data["replies"] = []

        if include_user:
            if self.author:
                data["user"] = self.author.to_dict()
            elif self.guest_name:
                data["user"] = {
                    "username": self.guest_name,
                    "avatar_url": "",
                    "is_admin": False,
                }

        # 标记当前用户是否已点赞
        if current_user_id:
            from models.like import CommentLike
            data["is_liked"] = CommentLike.query.filter_by(
                user_id=current_user_id, comment_id=self.id
            ).first() is not None

        return data
