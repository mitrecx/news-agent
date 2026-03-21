#!/usr/bin/env python3
"""更新用户密码的脚本"""

import asyncio
import bcrypt
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent.config import get_settings


async def update_password(username: str, new_password: str):
    """更新用户密码"""
    import asyncpg

    settings = get_settings()

    # 生成密码哈希
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    print(f"用户名: {username}")
    print(f"新密码: {new_password}")
    print(f"哈希后: {hashed_password[:50]}...")

    # 连接数据库
    conn = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )

    try:
        # 更新密码
        await conn.execute(
            "UPDATE users SET hashed_password = $1 WHERE username = $2",
            hashed_password,
            username
        )

        # 验证更新
        user = await conn.fetchrow(
            "SELECT id, username, email FROM users WHERE username = $1",
            username
        )

        if user:
            print(f"\n✅ 密码更新成功！")
            print(f"   用户ID: {user['id']}")
            print(f"   用户名: {user['username']}")
            print(f"   邮箱: {user['email']}")
        else:
            print(f"\n❌ 用户 '{username}' 不存在")

    finally:
        await conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python update_user_password.py <用户名> <新密码>")
        print("示例: python update_user_password.py test test123456")
        sys.exit(1)

    username = sys.argv[1]
    new_password = sys.argv[2]

    asyncio.run(update_password(username, new_password))
