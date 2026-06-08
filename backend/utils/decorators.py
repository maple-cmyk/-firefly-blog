from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from models.user import User

def admin_required(f):
    """装饰器：要求管理员权限"""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            user_id = int(get_jwt_identity())
        except Exception:
            return jsonify({"error": "需要登录"}), 401
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({"error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated
