import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # CORS
    origins = app.config["CORS_ORIGINS"].split(",")
    CORS(app, origins=[o.strip() for o in origins], supports_credentials=True)

    # 注册路由
    from routes.auth import auth_bp
    from routes.comments import comments_bp
    from routes.likes import likes_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(comments_bp, url_prefix="/api/comments")
    app.register_blueprint(likes_bp, url_prefix="/api/likes")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    # 健康检查
    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    # 开发阶段：创建数据库表（生产环境建议用 flask db upgrade）
    with app.app_context():
        try:
            from models.user import User
            from models.comment import Comment
            from models.like import CommentLike
            db.create_all()
            app.logger.info("Database tables created successfully")
        except Exception as e:
            app.logger.error(f"Database initialization failed: {e}")
            # 不阻止应用启动，表不存在时请求会报错但不会完全挂掉

    return app

# 直接运行时启动
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
