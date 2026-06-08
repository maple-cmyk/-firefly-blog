# Flask 评论系统 实施计划

> **For Hermes:** 使用 subagent-driven-development 执行此计划，逐任务推进。

**目标：** 为 Firefly-Astro 博客搭建 Flask 后端 + 完整评论系统（登录注册、头像、点赞、管理后台）

**架构：**
- 后端：Flask REST API（JWT 认证 + SQLAlchemy ORM），部署在 Railway
- 数据库：PostgreSQL（Railway 插件，免费额度）
- 前端：Svelte 评论组件嵌入 Astro，通过 fetch 调用 API
- 子域名：`api.maplecmyk.online` 指向 Flask 后端，`maplecmyk.online` 为博客

**技术栈：** Flask, SQLAlchemy, Flask-JWT-Extended, PostgreSQL, Svelte 5, Astro

---

## 项目结构

```
D:\Firefly-master\
├── src/
│   ├── components/comment/
│   │   ├── MapleComment.astro        # [新建] Astro 包装组件
│   │   └── MapleComment.svelte        # [新建] Svelte 评论 UI
│   ├── config/
│   │   └── commentConfig.ts           # [修改] 增加 maple 类型
│   └── types/
│       └── config.ts                  # [修改] CommentConfig 类型
│
backend/                               # [新建] Flask 后端项目
├── requirements.txt
├── Procfile                           # Railway 部署配置
├── app.py                             # 入口
├── config.py                          # 配置（数据库、JWT、CORS）
├── models/
│   ├── __init__.py
│   ├── user.py                       # User 模型
│   ├── comment.py                    # Comment 模型
│   └── like.py                       # Like 模型
├── routes/
│   ├── __init__.py
│   ├── auth.py                       # 注册/登录/刷新 token
│   ├── comments.py                   # 评论 CRUD
│   ├── likes.py                      # 点赞/取消
│   └── admin.py                      # 管理后台（审核/删除）
├── utils/
│   ├── __init__.py
│   └── decorators.py                 # JWT 装饰器
└── migrations/                        # Flask-Migrate
```

---

## 阶段一：后端基础设施

### Task 1: 初始化 Flask 项目结构

**目标：** 创建 backend 目录和基础文件

**文件：**
- 创建：`D:\Firefly-master\backend\requirements.txt`
- 创建：`D:\Firefly-master\backend\config.py`
- 创建：`D:\Firefly-master\backend\app.py`

**Step 1: 创建 requirements.txt**

```txt
flask==3.1.0
flask-cors==5.0.1
flask-sqlalchemy==3.1.1
flask-jwt-extended==4.7.1
flask-migrate==4.1.0
psycopg2-binary==2.9.10
werkzeug==3.1.3
gunicorn==23.0.0
python-dotenv==1.1.0
```

**Step 2: 创建 config.py**

```python
import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///comments.db"  # 本地开发用 SQLite
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:4321,https://maplecmyk.online")
```

**Step 3: 创建 app.py**

```python
import os
from flask import Flask
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
    CORS(app, origins=origins, supports_credentials=True)

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

    # 创建数据库表（SQLite 开发用）
    with app.app_context():
        db.create_all()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
```

**验证：**
```bash
cd backend && pip install -r requirements.txt && python -c "from app import create_app; app = create_app(); print('App created OK')"
```

---

## 阶段二：数据模型

### Task 2: 创建 User 模型

**目标：** 用户注册/登录的数据模型

**文件：**
- 创建：`backend/models/__init__.py`
- 创建：`backend/models/user.py`

**代码：`models/__init__.py`**
```python
from models.user import User
from models.comment import Comment
from models.like import CommentLike
```

**代码：`models/user.py`**
```python
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar_url = db.Column(db.String(500), default="")
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    comments = db.relationship("Comment", backref="author", lazy="dynamic")
    likes = db.relationship("CommentLike", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat(),
        }
```

**验证：**
```bash
cd backend && python -c "from app import create_app, db; app = create_app(); print('User model OK')"
```

---

### Task 3: 创建 Comment 模型

**目标：** 评论数据结构，支持嵌套回复

**文件：**
- 创建：`backend/models/comment.py`

**代码：**
```python
from datetime import datetime
from app import db

class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    post_slug = db.Column(db.String(500), nullable=False, index=True)  # 文章路径
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)
    likes_count = db.Column(db.Integer, default=0)
    is_approved = db.Column(db.Boolean, default=True)  # 默认自动通过
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    replies = db.relationship(
        "Comment", backref=db.backref("parent", remote_side=[id]),
        lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self, include_user=True):
        data = {
            "id": self.id,
            "post_slug": self.post_slug,
            "content": self.content,
            "parent_id": self.parent_id,
            "likes_count": self.likes_count,
            "is_approved": self.is_approved,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "replies": [r.to_dict(include_user=include_user) for r in self.replies]
            if not self.parent_id else [],
        }
        if include_user and self.author:
            data["user"] = self.author.to_dict()
            data["user"]["is_liked"] = False  # 前端填充
        return data
```

**验证：**
```bash
cd backend && python -c "from app import create_app; app = create_app(); print('Comment model OK')"
```

---

### Task 4: 创建 Like 模型

**目标：** 点赞记录

**文件：**
- 创建：`backend/models/like.py`

**代码：**
```python
from datetime import datetime
from app import db

class CommentLike(db.Model):
    __tablename__ = "comment_likes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "comment_id", name="uq_user_comment_like"),
    )
```

---

## 阶段三：API 路由

### Task 5: 用户认证路由（注册/登录）

**目标：** JWT 注册和登录 API

**文件：**
- 创建：`backend/routes/__init__.py`
- 创建：`backend/routes/auth.py`
- 创建：`backend/utils/__init__.py`
- 创建：`backend/utils/decorators.py`

**代码：`routes/auth.py`**
```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from app import db
from models.user import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"error": "所有字段都是必填的"}), 400
    if len(username) < 2 or len(username) > 50:
        return jsonify({"error": "用户名需要 2-50 个字符"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码至少 6 个字符"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "用户名已存在"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "邮箱已注册"}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "user": user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "邮箱或密码错误"}), 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "user": user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token,
    })

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    return jsonify({"user": user.to_dict()})

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return jsonify({"access_token": access_token})
```

**API 端点：**
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 |
| GET | `/api/auth/me` | 获取当前用户 |
| POST | `/api/auth/refresh` | 刷新 access_token |

---

### Task 6: 评论 CRUD 路由

**目标：** 获取/创建/删除评论 API

**文件：**
- 创建：`backend/routes/comments.py`

**代码：**
```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, optional_jwt
from app import db
from models.comment import Comment
from models.user import User
from models.like import CommentLike

comments_bp = Blueprint("comments", __name__)

@comments_bp.route("/<path:post_slug>", methods=["GET"])
@optional_jwt()
def get_comments(post_slug):
    """获取文章的所有评论（树形结构）"""
    comments = (
        Comment.query
        .filter_by(post_slug=post_slug, parent_id=None, is_approved=True)
        .order_by(Comment.created_at.desc())
        .all()
    )

    current_user_id = None
    try:
        current_user_id = int(get_jwt_identity())
    except Exception:
        pass

    result = []
    for c in comments:
        d = c.to_dict(include_user=True)
        # 标记当前用户是否已点赞
        if current_user_id:
            d["user"]["is_liked"] = CommentLike.query.filter_by(
                user_id=current_user_id, comment_id=c.id
            ).first() is not None
            for r in d.get("replies", []):
                r["user"]["is_liked"] = CommentLike.query.filter_by(
                    user_id=current_user_id, comment_id=r["id"]
                ).first() is not None
        result.append(d)

    return jsonify({"comments": result, "count": len(result)})

@comments_bp.route("/<path:post_slug>", methods=["POST"])
@jwt_required()
def create_comment(post_slug):
    """发表评论"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
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

    return jsonify({"comment": comment.to_dict()}), 201

@comments_bp.route("/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def delete_comment(comment_id):
    """删除自己的评论"""
    user_id = int(get_jwt_identity())
    comment = Comment.query.get(comment_id)

    if not comment:
        return jsonify({"error": "评论不存在"}), 404
    if comment.user_id != user_id:
        # 管理员也可以删除
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({"error": "无权删除此评论"}), 403

    # 级联软删除（标记未批准）
    def soft_delete(c):
        c.is_approved = False
        for reply in c.replies:
            soft_delete(reply)

    soft_delete(comment)
    db.session.commit()

    return jsonify({"message": "评论已删除"})
```

**API 端点：**
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/comments/<post_slug>` | 获取评论列表 |
| POST | `/api/comments/<post_slug>` | 发表评论 |
| DELETE | `/api/comments/<comment_id>` | 删除评论 |

---

### Task 7: 点赞路由

**目标：** 点赞/取消点赞 API

**文件：**
- 创建：`backend/routes/likes.py`

**代码：**
```python
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models.comment import Comment
from models.like import CommentLike

likes_bp = Blueprint("likes", __name__)

@likes_bp.route("/<int:comment_id>/toggle", methods=["POST"])
@jwt_required()
def toggle_like(comment_id):
    """点赞/取消点赞"""
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
```

---

### Task 8: 管理后台路由

**目标：** 管理员审核和用户管理

**文件：**
- 创建：`backend/routes/admin.py`

**代码：**
```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models.user import User
from models.comment import Comment

admin_bp = Blueprint("admin", __name__)

def admin_required():
    """检查是否为管理员，返回 user 或 error"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user or not user.is_admin:
        return None, (jsonify({"error": "需要管理员权限"}), 403)
    return user, None

@admin_bp.route("/comments/pending", methods=["GET"])
@jwt_required()
def pending_comments():
    """获取待审核评论"""
    user, err = admin_required()
    if err:
        return err
    comments = Comment.query.filter_by(is_approved=False).order_by(Comment.created_at.desc()).all()
    return jsonify({"comments": [c.to_dict() for c in comments]})

@admin_bp.route("/comments/<int:comment_id>/approve", methods=["POST"])
@jwt_required()
def approve_comment(comment_id):
    """审核通过"""
    user, err = admin_required()
    if err:
        return err
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({"error": "评论不存在"}), 404
    comment.is_approved = True
    db.session.commit()
    return jsonify({"message": "审核通过"})

@admin_bp.route("/comments/<int:comment_id>/reject", methods=["POST"])
@jwt_required()
def reject_comment(comment_id):
    """拒绝并删除"""
    user, err = admin_required()
    if err:
        return err
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({"error": "评论不存在"}), 404
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"message": "已拒绝并删除"})

@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    """管理后台统计"""
    user, err = admin_required()
    if err:
        return err
    total_comments = Comment.query.count()
    total_users = User.query.count()
    total_likes = sum(c.likes_count for c in Comment.query.all())
    return jsonify({
        "total_comments": total_comments,
        "total_users": total_users,
        "total_likes": total_likes,
    })
```

---

## 阶段四：前端评论组件

### Task 9: 创建 Svelte 评论组件

**目标：** 完整的评论 UI（列表 + 发表 + 登录 + 点赞 + 回复）

**文件：**
- 创建：`src/components/comment/MapleComment.svelte`

**关键功能：**
- 评论列表（树形嵌套）+ 加载状态
- 登录/注册表单（弹窗）
- 发表评论 + 回复表单
- 点赞按钮（数字 + 动画）
- 时间显示（刚刚 / N分钟前 / N天前）
- 头像 + 用户名展示
- 删除按钮（仅自己的评论）
- 加载骨架屏
- 错误提示 toast
- 暗色模式适配

---

### Task 10: 创建 Astro 评论包装组件

**目标：** Astro 包装器，传递参数给 Svelte 组件

**文件：**
- 创建：`src/components/comment/MapleComment.astro`

**代码：**
```astro
---
import { commentConfig } from "@/config/commentConfig";
import MapleComment from "./MapleComment.svelte";

interface Props {
    path: string;
    title?: string;
}

const { path, title } = Astro.props;
const config = commentConfig.maple!;
---
<div class="maple-comment-wrapper">
    <MapleComment
        postSlug={path}
        postTitle={title}
        apiUrl={config.apiUrl}
        client:load
    />
</div>
```

---

### Task 11: 更新配置和类型定义

**目标：** 将 maple 评论类型集成到现有框架

**要修改的文件：**

1. **`src/types/config.ts`** — CommentConfig 类型增加 `"maple"`:
```typescript
type: "none" | "twikoo" | "waline" | "giscus" | "disqus" | "artalk" | "maple";
// 新增 maple 配置
maple?: {
    apiUrl: string;  // Flask 后端地址
};
```

2. **`src/config/commentConfig.ts`** — 增加 maple 配置:
```typescript
type: "maple",  // 暂设为 none，部署后改
maple: {
    apiUrl: "http://localhost:5000",  // 本地开发；生产改为 https://api.maplecmyk.online
},
```

3. **`src/components/comment/index.astro`** — 增加 maple 分支:
```astro
import MapleComment from "./MapleComment.astro";
// ...
{commentService === "maple" && <MapleComment path={path} title={customTitle || postTitle || slug} />}
```

---

## 阶段五：部署

### Task 12: Railway 部署配置

**目标：** 部署 Flask 后端到 Railway

**文件：**
- 创建：`backend/Procfile`
- 创建：`backend/.env.example`

**Procfile：**
```
web: gunicorn app:create_app()
```

**.env.example：**
```
SECRET_KEY=生成一个随机字符串
JWT_SECRET_KEY=再生成一个随机字符串
DATABASE_URL=postgresql://...  # Railway 自动注入
CORS_ORIGINS=http://localhost:4321,https://maplecmyk.online
```

**Railway 部署步骤：**
1. 在 Railway 创建新项目
2. 连接 GitHub 仓库（`maple-cmyk/-firefly-blog`，选择 `backend/` 子目录）
3. Railway 自动检测 Python + Procfile
4. 添加 PostgreSQL 插件
5. 设置环境变量 `SECRET_KEY`、`JWT_SECRET_KEY`
6. 部署域名（如 `maple-comments.up.railway.app`）

---

### Task 13: DNS 配置

**目标：** 设置子域名 `api.maplecmyk.online`

**操作步骤：**
1. 登录 Spaceship 域名管理
2. 添加 CNAME 记录：`api` → Railway 提供的域名
3. 更新 `CORS_ORIGINS` 环境变量（如有需要）
4. 更新 `commentConfig.ts` 中 `apiUrl` 为 `https://api.maplecmyk.online`

---

## 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据库 | PostgreSQL (Railway) | 免费持久化，不怕重启丢数据 |
| 认证 | JWT (access + refresh) | 无状态，适合 API |
| 审核策略 | 默认自动通过 | 降低摩擦，管理员可事后处理 |
| 头像 | Gravatar 回退 + 默认头像 | 不需要文件上传，降低复杂度 |
| 前端框架 | Svelte 5 | 与 Firefly 主题一致 |
| 评论排序 | 最新在前 | 博客场景常见做法 |

---

## 后续可选增强

- [ ] 邮件验证（注册确认）
- [ ] 头像上传
- [ ] Markdown 支持
- [ ] 评论通知（邮件/Webhook）
- [ ] 反垃圾（Akismet 集成）
- [ ] IP 限流（Flask-Limiter）
- [ ] 管理后台 Web UI（独立页面）
