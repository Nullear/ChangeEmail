from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import PersonNormalMessageReceived, GroupNormalMessageReceived
import sqlite3
import hashlib
import os

"""
实现 changeEmail 指令功能：
1. 解析指令参数，验证格式有效性
2. 连接 sqlite 数据库验证用户名密码（SHA-256 比对）
3. 密码正确时修改邮箱并撤回用户指令，错误时提示对应信息
"""


class ChangeEmail(BasePlugin):
    def __init__(self, host: APIHost):
        # 初始化数据库路径（从 main.py 所在目录向上导航至 arcaea_database.db）
        self.db_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),  # 当前 main.py 目录
                "../../../../",  # 向上导航至 Server-Urcaea 目录
                "database/arcaea_database.db"  # 数据库相对路径
            )
        )
        self.ap.logger.debug(f"数据库路径初始化：{self.db_path}")
        pass

    async def initialize(self):
        pass

    # 处理私聊消息中的 changeEmail 指令
    @handler(PersonNormalMessageReceived)
    async def handle_private_change_email(self, ctx: EventContext):
        await self._process_change_email(ctx)

    # 处理群聊消息中的 changeEmail 指令
    @handler(GroupNormalMessageReceived)
    async def handle_group_change_email(self, ctx: EventContext):
        await self._process_change_email(ctx)

    # 统一的 changeEmail 指令处理逻辑
    async def _process_change_email(self, ctx: EventContext):
        msg = ctx.event.text_message.strip()
        parts = msg.split()  # 分割指令为列表

        # 1. 指令格式有效性判断
        if len(parts) != 4 or parts[0] != "changeEmail":
            # 仅在指令前缀为 changeEmail 时才提示用法（避免干扰其他消息）
            if parts and parts[0] == "changeEmail":
                ctx.add_return("reply", ["用法：changeEmail <Username> <Password> <YourQQ>"])
            return

        # 提取指令参数
        username = parts[1]
        input_password = parts[2]
        your_qq = parts[3]
        self.ap.logger.debug(f"收到 changeEmail 指令：用户名={username}, QQ={your_qq}")

        # 2. 数据库操作：验证密码并修改邮箱
        try:
            # 连接数据库（sqlite3 同步操作，此处简化处理）
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                cursor = conn.cursor()

                # 2.1 查询用户名对应的密码（SHA-256 存储）
                cursor.execute("SELECT password FROM user WHERE name = ?", (username,))
                result = cursor.fetchone()

                if not result:
                    # 用户名不存在
                    ctx.add_return("reply", ["用户名或密码错误"])
                    return

                db_password = result[0]  # 数据库中存储的 SHA-256 加密密码

                # 2.2 计算输入密码的 SHA-256 哈希（与数据库存储格式对齐）
                hashed_input = hashlib.sha256(input_password.encode("utf-8")).hexdigest()

                if hashed_input != db_password:
                    # 密码不匹配
                    ctx.add_return("reply", ["用户名或密码错误"])
                    return

                # 2.3 密码正确：修改邮箱（YourQQ + @qq.com）
                new_email = f"{your_qq}@qq.com"
                cursor.execute(
                    "UPDATE user SET email = ? WHERE name = ?",
                    (new_email, username)
                )
                conn.commit()
                self.ap.logger.debug(f"邮箱修改成功：{username} -> {new_email}")

                # 3. 隐私保护：撤回用户发送的指令（依赖 LangBot 事件返回支持）
                ctx.add_return("recall", True)  # 触发消息撤回
                # 回复修改成功提示
                ctx.add_return("reply", [f"邮箱修改成功，新邮箱为：{new_email}"])

        except sqlite3.Error as e:
            # 数据库操作异常处理
            error_msg = f"数据库错误：{str(e)}"
            self.ap.logger.error(error_msg)
            ctx.add_return("reply", [error_msg])
        except Exception as e:
            # 其他未知异常
            error_msg = f"处理失败：{str(e)}"
            self.ap.logger.error(error_msg)
            ctx.add_return("reply", [error_msg])

    def __del__(self):
        pass


# 注册插件（必须调用，插件名称与类名无关）
register(ChangeEmail, "ChangeEmail")
