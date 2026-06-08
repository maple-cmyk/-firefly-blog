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

            # 迁移：添加游客评论字段（v2）
            from sqlalchemy import text, inspect
            inspector = inspect(db.engine)
            existing_cols = [c["name"] for c in inspector.get_columns("comments")]

            if "guest_name" not in existing_cols:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE comments ADD COLUMN guest_name VARCHAR(50)"))
                    conn.execute(text("ALTER TABLE comments ADD COLUMN guest_email VARCHAR(120)"))
                    conn.execute(text("ALTER TABLE comments ALTER COLUMN user_id DROP NOT NULL"))
                    conn.commit()
                app.logger.info("Migration: added guest_name/guest_email columns")

            # 迁移：添加 QQ 字段（v3）
            if "guest_qq" not in existing_cols:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE comments ADD COLUMN guest_qq VARCHAR(20)"))
                    conn.commit()
                app.logger.info("Migration: added guest_qq column")
        except Exception as e:
            app.logger.error(f"Database initialization failed: {e}")

    return app

# 直接运行时启动
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
