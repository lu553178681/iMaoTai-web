"""
Flask-Login 兼容性修复

此模块解决了Flask-Login在某些Python环境下的兼容性问题。
主要是修复了Flask-Login中User类的is_authenticated、is_active和is_anonymous属性。
"""

from flask_login import UserMixin

# 重写UserMixin中的属性方法，确保兼容性
UserMixin.is_authenticated = property(lambda self: True)
UserMixin.is_active = property(lambda self: True)
UserMixin.is_anonymous = property(lambda self: False)

# 不执行任何操作，只是为了兼容性
def init_app(app):
    """空方法，保持API兼容性"""
    pass 