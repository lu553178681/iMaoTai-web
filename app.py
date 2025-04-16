from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, TimeField, HiddenField, TextAreaField, SelectMultipleField, widgets
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Regexp, Optional
import os
# 导入修复程序
import fix_flask_login
import config
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import json
import threading
import time
import random
import configparser
import privateCrypt
import process
import send_message
from dotenv import load_dotenv
import requests
from commodity_fetcher import CommodityFetcher

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

# 创建自定义多选字段
class MultipleCheckboxField(SelectMultipleField):
    """
    自定义多选字段，渲染为一组复选框
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

# 初始化Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)
    # 定义关系
    reservations = db.relationship('Reservation', backref='user', lazy=True, cascade="all, delete-orphan")
    tasks = db.relationship('TaskSetting', backref='user', lazy=True, cascade="all, delete-orphan")
    mt_accounts = db.relationship('MaotaiAccount', backref='user', lazy=True, cascade="all, delete-orphan")
    push_settings = db.relationship('UserPushSetting', backref='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('确认密码', 
                                   validators=[DataRequired(), EqualTo('password', message='两次输入的密码必须一致')])
    submit = SubmitField('注册')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        # 获取用户统计信息
        account_count = MaotaiAccount.query.filter_by(user_id=current_user.id).count()
        active_account_count = MaotaiAccount.query.filter_by(user_id=current_user.id, is_active=True).count()
        
        task_count = TaskSetting.query.filter_by(user_id=current_user.id).count()
        active_task_count = TaskSetting.query.filter_by(user_id=current_user.id, enabled=True).count()
        
        reservation_count = Reservation.query.filter_by(user_id=current_user.id).count()
        success_count = Reservation.query.filter_by(user_id=current_user.id, status='成功').count()
        
        # 最近的5条预约记录
        recent_reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(
            Reservation.create_time.desc()
        ).limit(5).all()
        
        return render_template('home.html', 
                             account_count=account_count,
                             active_account_count=active_account_count,
                             task_count=task_count,
                             active_task_count=active_task_count,
                             reservation_count=reservation_count,
                             success_count=success_count,
                             recent_reservations=recent_reservations)
    return render_template('home.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('账号创建成功，请登录!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('当前密码', validators=[DataRequired()])
    new_password = PasswordField('新密码', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('确认新密码', 
                                   validators=[DataRequired(), EqualTo('new_password', message='两次输入的密码必须一致')])
    submit = SubmitField('修改密码')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            # 更新最后登录时间
            user.last_login = datetime.datetime.now()
            db.session.commit()
            
            flash('登录成功!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('登录失败，请检查用户名和密码', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_code = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)
    reserve_time = db.Column(db.DateTime, nullable=True)
    mt_account_id = db.Column(db.Integer, db.ForeignKey('maotai_account.id'), nullable=True)
    
    # 关联茅台账号
    mt_account = db.relationship('MaotaiAccount', backref='reservations', lazy=True)

class TaskSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_code = db.Column(db.String(20), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    preferred_time = db.Column(db.Time, default=datetime.time(9, 0))
    mt_account_id = db.Column(db.Integer, db.ForeignKey('maotai_account.id'), nullable=True)
    last_run = db.Column(db.DateTime, nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)
    
    # 关联茅台账号
    mt_account = db.relationship('MaotaiAccount', backref='tasks', lazy=True)

class TaskItemMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task_setting.id', ondelete='CASCADE'), nullable=False)
    item_code = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    
    # 关联任务
    task = db.relationship('TaskSetting', backref=db.backref('item_mappings', cascade='all, delete-orphan'), lazy=True)

class ReservationForm(FlaskForm):
    item_codes = MultipleCheckboxField('商品类型(可多选)', validators=[], choices=[])
    submit = SubmitField('提交预约')

class TaskSettingForm(FlaskForm):
    item_codes = MultipleCheckboxField('商品类型(可多选)', validators=[], choices=[])
    mt_account_id = SelectField('使用账号', validators=[DataRequired()], coerce=int)
    enabled = BooleanField('启用自动预约', default=True)
    preferred_time = TimeField('首选预约时间', default=datetime.time(9, 0), validators=[DataRequired()])
    submit = SubmitField('保存设置')

@app.route('/reservations')
@login_required
def reservations():
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 限制每页显示数量的选项
    if per_page not in [10, 20, 50, 100]:
        per_page = 10
    
    # 查询预约记录并分页
    pagination = Reservation.query.filter_by(user_id=current_user.id).join(
        MaotaiAccount, Reservation.mt_account_id == MaotaiAccount.id, isouter=True
    ).order_by(
        Reservation.create_time.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    user_reservations = pagination.items
    
    return render_template('reservations.html', 
                        reservations=user_reservations, 
                        pagination=pagination,
                        per_page=per_page)

@app.route('/create_reservation', methods=['GET', 'POST'])
@login_required
def create_reservation():
    # 重定向到任务页面，移除预约创建界面
    flash('直接预约功能已被禁用，请使用自动预约功能', 'info')
    return redirect(url_for('tasks'))
    
    # 原代码被移除，保留路由功能，但不再显示预约创建界面

@app.route('/delete_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def delete_reservation(reservation_id):
    # 只允许管理员删除预约记录
    if current_user.username != 'admin' and current_user.id != 1:
        flash('您没有权限执行此操作！', 'danger')
        return redirect(url_for('reservations'))
    
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # 保存一些信息用于提示
    item_code = reservation.item_code
    item_name = ""
    if item_code in config.ITEM_CONFIG:
        item_name = config.ITEM_CONFIG[item_code]['name']
    elif item_code in config.ITEM_MAP:
        item_name = config.ITEM_MAP[item_code]
    else:
        item_name = item_code
    
    # 删除预约记录
    db.session.delete(reservation)
    db.session.commit()
    
    flash(f'已成功删除预约记录：{item_name}', 'success')
    return redirect(url_for('reservations'))

@app.route('/clear_all_reservations', methods=['POST'])
@login_required
def clear_all_reservations():
    # 只允许管理员清空预约记录
    if current_user.username != 'admin' and current_user.id != 1:
        flash('您没有权限执行此操作！', 'danger')
        return redirect(url_for('reservations'))
    
    # 获取当前系统中的所有预约记录数量
    reservation_count = Reservation.query.count()
    
    # 删除所有预约记录
    Reservation.query.delete()
    db.session.commit()
    
    flash(f'已成功清空所有预约记录，共删除 {reservation_count} 条记录', 'success')
    return redirect(url_for('reservations'))

@app.route('/tasks')
@login_required
def tasks():
    user_tasks = TaskSetting.query.filter_by(user_id=current_user.id).all()
    return render_template('tasks.html', tasks=user_tasks)

@app.route('/create_task', methods=['GET', 'POST'])
@login_required
def create_task():
    form = TaskSettingForm()
    
    # 动态获取当前用户的茅台账号列表
    user_accounts = MaotaiAccount.query.filter_by(user_id=current_user.id, is_active=True).all()
    form.mt_account_id.choices = [(account.id, f"{account.hidemobile} ({account.province}, {account.city})") for account in user_accounts]
    
    if not user_accounts:
        flash('您需要先添加茅台账号才能创建自动预约任务！', 'warning')
        return redirect(url_for('accounts'))
    
    # 获取商品列表并设置为表单字段的选项
    try:
        # 使用CommodityFetcher类直接获取商品列表
        fetcher = CommodityFetcher()
        products = fetcher.fetch_commodities()
        
        if products:
            # 存储sessionId到会话中，后续获取店铺列表时使用
            session['mt_session_id'] = fetcher.session_id
            
            # 设置表单字段的选项
            choices = []
            for product in products:
                item_id = product['Code']
                title = product['Title']
                choices.append((item_id, title))
            
            # 更新表单字段的选项
            form.item_codes.choices = choices
    except Exception as e:
        # 出错时不阻止页面加载，页面会通过JS获取商品列表
        print(f"预加载商品列表出错: {str(e)}")
    
    if form.validate_on_submit():
        # 获取所有选中的商品
        selected_item_codes = request.form.getlist('item_codes')
        
        # 如果没有选择任何商品，直接返回成功信息
        if not selected_item_codes:
            flash('您没有选择任何商品，任务已保存！', 'success')
            return redirect(url_for('tasks'))
            
        # 创建新任务
        task = TaskSetting(
            user_id=current_user.id,
            item_code=selected_item_codes[0] if selected_item_codes else '',  # 兼容旧版
            mt_account_id=form.mt_account_id.data,
            enabled=form.enabled.data,
            preferred_time=form.preferred_time.data
        )
        db.session.add(task)
        db.session.flush()  # 获取task.id
        
        # 为每个选择的商品创建映射
        for item_code in selected_item_codes:
            item_mapping = TaskItemMapping(
                task_id=task.id,
                item_code=item_code
            )
            db.session.add(item_mapping)
        
        db.session.commit()
        
        # 构建消息推送内容
        account = MaotaiAccount.query.get(form.mt_account_id.data)
        account_info = f"{account.hidemobile} ({account.province}, {account.city})" if account else "未知账号"
        
        item_names = []
        
        # 获取商品信息
        try:
            result = process.get_product_list()
            if result['success']:
                items_dict = {item['itemId']: item['title'] for item in result['items']}
                
                for item_code in selected_item_codes:
                    if item_code in items_dict:
                        item_names.append(items_dict[item_code])
                    elif item_code in config.ITEM_CONFIG:
                        item_names.append(config.ITEM_CONFIG[item_code]['name'])
                    elif item_code in config.ITEM_MAP:
                        item_names.append(config.ITEM_MAP[item_code])
                    else:
                        item_names.append(item_code)
            else:
                # 如果无法获取商品详情，则使用配置或简单ID
                for item_code in selected_item_codes:
                    if item_code in config.ITEM_CONFIG:
                        item_names.append(config.ITEM_CONFIG[item_code]['name'])
                    elif item_code in config.ITEM_MAP:
                        item_names.append(config.ITEM_MAP[item_code])
                    else:
                        item_names.append(item_code)
        except Exception:
            # 发生错误时使用简单商品ID
            for item_code in selected_item_codes:
                if item_code in config.ITEM_CONFIG:
                    item_names.append(config.ITEM_CONFIG[item_code]['name'])
                elif item_code in config.ITEM_MAP:
                    item_names.append(config.ITEM_MAP[item_code])
                else:
                    item_names.append(item_code)
                
        formatted_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_status = "已启用" if form.enabled.data else "已禁用"
        preferred_time = form.preferred_time.data.strftime('%H:%M')
        action_type = "更新" if task.id > 0 else "创建"
        
        message_content = f"""
用户: {current_user.username}
{action_type}时间: {formatted_time}
使用账号: {account_info}
预约时间: {preferred_time}
状态: {task_status}
商品列表:
{chr(10).join(['- ' + name for name in item_names])}
        """
        
        # 发送消息推送
        push_success = False
        if config.PUSH_TOKEN:
            push_success = send_message.send_pushplus(config.PUSH_TOKEN, f"【{action_type}】茅台自动预约任务", message_content)
        if not push_success and config.DINGTALK_WEBHOOK:
            send_message.send_webhook(config.DINGTALK_WEBHOOK, f"【{action_type}】茅台自动预约任务", message_content)
        if config.SCKEY:
            send_message.send_server_chan(config.SCKEY, f"【{action_type}】茅台自动预约任务", message_content)
        
        flash(f'已{action_type} {len(selected_item_codes)} 个商品的自动预约任务!', 'success')
        return redirect(url_for('tasks'))
    
    return render_template('create_task.html', form=form)

@app.route('/toggle_task/<int:task_id>', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = TaskSetting.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('您无权修改此任务!', 'danger')
        return redirect(url_for('tasks'))
    
    task.enabled = not task.enabled
    db.session.commit()
    
    return redirect(url_for('tasks'))

@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = TaskSetting.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('您无权删除此任务!', 'danger')
        return redirect(url_for('tasks'))
    
    db.session.delete(task)
    db.session.commit()
    flash('任务已删除!', 'success')
    
    return redirect(url_for('tasks'))

@app.route('/run_task/<int:task_id>', methods=['POST'])
@login_required
def run_task(task_id):
    task = TaskSetting.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('您无权执行此任务!', 'danger')
        return redirect(url_for('tasks'))
    
    # 执行实际预约过程
    success, message = real_reservation(task)
    
    if success:
        flash('所有商品预约成功!', 'success')
    else:
        # 获取此任务的所有商品
        item_codes = []
        item_mappings = TaskItemMapping.query.filter_by(task_id=task.id).all()
        if item_mappings:
            item_codes = [mapping.item_code for mapping in item_mappings]
        else:
            item_codes = [task.item_code]
            
        # 获取刚刚预约的结果
        results = []
        success_count = 0
        total_count = len(item_codes)
        
        for item_code in item_codes:
            # 查找最近的预约记录
            reservation = Reservation.query.filter_by(
                user_id=current_user.id,
                item_code=item_code
            ).order_by(Reservation.create_time.desc()).first()
            
            if reservation and reservation.create_time >= datetime.datetime.now() - datetime.timedelta(minutes=5):
                item_name = item_code
                if item_code in config.ITEM_CONFIG:
                    item_name = config.ITEM_CONFIG[item_code]['name']
                elif item_code in config.ITEM_MAP:
                    item_name = config.ITEM_MAP[item_code]
                
                status = reservation.status
                if status == '成功':
                    success_count += 1
                    
                results.append(f"{item_name}: {status}")
        
        # 生成预约结果消息
        if success_count == 0:
            status_prefix = "预约失败"
        elif success_count < total_count:
            status_prefix = "部分商品预约成功"
        else:
            status_prefix = "所有商品预约成功"
            
        flash(f'{status_prefix}! 预约结果: {", ".join(results)}', 'warning' if success_count < total_count else 'success')
    
    return redirect(url_for('tasks'))

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    # 查询并验证任务
    task = TaskSetting.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('您无权编辑此任务!', 'danger')
        return redirect(url_for('tasks'))
    
    # 初始化表单
    form = TaskSettingForm(obj=task)
    
    # 动态获取当前用户的茅台账号列表
    user_accounts = MaotaiAccount.query.filter_by(user_id=current_user.id, is_active=True).all()
    form.mt_account_id.choices = [(account.id, f"{account.hidemobile} ({account.province}, {account.city})") for account in user_accounts]
    
    # 获取此任务已选择的商品
    selected_items = [mapping.item_code for mapping in TaskItemMapping.query.filter_by(task_id=task.id).all()]
    
    # 获取商品列表并设置为表单字段的选项
    try:
        # 使用CommodityFetcher类直接获取商品列表
        fetcher = CommodityFetcher()
        products = fetcher.fetch_commodities()
        
        if products:
            # 存储sessionId到会话中，后续获取店铺列表时使用
            session['mt_session_id'] = fetcher.session_id
            
            # 设置表单字段的选项
            choices = []
            for product in products:
                item_id = product['Code']
                title = product['Title']
                choices.append((item_id, title))
            
            # 更新表单字段的选项
            form.item_codes.choices = choices
    except Exception as e:
        # 出错时不阻止页面加载，页面会通过JS获取商品列表
        print(f"预加载商品列表出错: {str(e)}")
    
    if form.validate_on_submit():
        # 获取所有选中的商品
        selected_item_codes = request.form.getlist('item_codes')
        
        # 如果没有选择任何商品，直接返回成功信息
        if not selected_item_codes:
            flash('您没有选择任何商品，任务已保存！', 'success')
            return redirect(url_for('tasks'))
        
        # 更新任务信息
        task.mt_account_id = form.mt_account_id.data
        task.enabled = form.enabled.data
        task.preferred_time = form.preferred_time.data
        task.item_code = selected_item_codes[0] if selected_item_codes else ''  # 兼容旧版
        
        # 删除旧的商品映射
        TaskItemMapping.query.filter_by(task_id=task.id).delete()
        
        # 为每个选择的商品创建映射
        for item_code in selected_item_codes:
            item_mapping = TaskItemMapping(
                task_id=task.id,
                item_code=item_code
            )
            db.session.add(item_mapping)
        
        db.session.commit()
        
        # 构建消息推送内容
        account = MaotaiAccount.query.get(form.mt_account_id.data)
        account_info = f"{account.hidemobile} ({account.province}, {account.city})" if account else "未知账号"
        
        item_names = []
        
        # 获取商品信息
        try:
            result = process.get_product_list()
            if result['success']:
                items_dict = {item['itemId']: item['title'] for item in result['items']}
                
                for item_code in selected_item_codes:
                    if item_code in items_dict:
                        item_names.append(items_dict[item_code])
                    elif item_code in config.ITEM_CONFIG:
                        item_names.append(config.ITEM_CONFIG[item_code]['name'])
                    elif item_code in config.ITEM_MAP:
                        item_names.append(config.ITEM_MAP[item_code])
                    else:
                        item_names.append(item_code)
            else:
                # 如果无法获取商品详情，则使用配置或简单ID
                for item_code in selected_item_codes:
                    if item_code in config.ITEM_CONFIG:
                        item_names.append(config.ITEM_CONFIG[item_code]['name'])
                    elif item_code in config.ITEM_MAP:
                        item_names.append(config.ITEM_MAP[item_code])
                    else:
                        item_names.append(item_code)
        except Exception:
            # 发生错误时使用简单商品ID
            for item_code in selected_item_codes:
                if item_code in config.ITEM_CONFIG:
                    item_names.append(config.ITEM_CONFIG[item_code]['name'])
                elif item_code in config.ITEM_MAP:
                    item_names.append(config.ITEM_MAP[item_code])
                else:
                    item_names.append(item_code)
                
        formatted_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_status = "已启用" if form.enabled.data else "已禁用"
        preferred_time = form.preferred_time.data.strftime('%H:%M')
        
        message_content = f"""
用户: {current_user.username}
更新时间: {formatted_time}
使用账号: {account_info}
预约时间: {preferred_time}
状态: {task_status}
商品列表:
{chr(10).join(['- ' + name for name in item_names])}
        """
        
        # 发送消息推送
        push_success = False
        if config.PUSH_TOKEN:
            push_success = send_message.send_pushplus(config.PUSH_TOKEN, f"【更新】茅台自动预约任务", message_content)
        if not push_success and config.DINGTALK_WEBHOOK:
            send_message.send_webhook(config.DINGTALK_WEBHOOK, f"【更新】茅台自动预约任务", message_content)
        if config.SCKEY:
            send_message.send_server_chan(config.SCKEY, f"【更新】茅台自动预约任务", message_content)
        
        flash(f'已更新 {len(selected_item_codes)} 个商品的自动预约任务!', 'success')
        return redirect(url_for('tasks'))
    
    # 设置表单初始值
    if selected_items:
        form.item_codes.data = selected_items
    
    return render_template('edit_task.html', form=form, task=task)

def real_reservation(task):
    """实际预约过程，使用茅台账号信息调用预约API"""
    print(f"\n[{datetime.datetime.now()}] ==== 开始执行实际预约过程 ==== ")
    # 获取任务关联的茅台账号
    account = MaotaiAccount.query.filter_by(id=task.mt_account_id).first()
    
    if not account:
        print(f"[{datetime.datetime.now()}] 预约失败: 找不到关联的茅台账号")
        return False, "预约失败: 找不到关联的茅台账号"
    
    if not account.is_active:
        print(f"[{datetime.datetime.now()}] 预约失败: 账号已被禁用")
        return False, "预约失败: 账号已被禁用"
    
    # 解密敏感信息
    try:
        # 重用已有的AES密钥
        key = privateCrypt.get_aes_key()
        
        # 解密手机号和用户ID
        mobile = privateCrypt.decrypt_aes_ecb(account.mobile, key)
        user_id = privateCrypt.decrypt_aes_ecb(account.userid, key)
        
        print(f"[{datetime.datetime.now()}] 解密账号信息成功: 手机号={mobile[:3]}****{mobile[-4:]}, 用户ID={user_id}")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] 解密账号信息出错: {str(e)}")
        return False, f"预约失败: 解密账号信息出错 - {str(e)}"
    
    # 调用预约API
    try:
        # 初始化headers
        print(f"[{datetime.datetime.now()}] 初始化headers: token={account.token}")
        process.init_headers(user_id=user_id, token=account.token, lat=account.lat, lng=account.lng)
        
        # 检查headers是否包含必要的信息
        required_headers = ["userId", "MT-Token", "MT-Lat", "MT-Lng", "MT-APP-Version"]
        for header in required_headers:
            if header not in process.headers or not process.headers[header]:
                print(f"[{datetime.datetime.now()}] 警告: 缺少必要的header: {header}={process.headers.get(header, '缺失')}")
        
        # 获取当前会话ID
        print(f"[{datetime.datetime.now()}] 获取当前会话ID")
        process.get_current_session_id()
        print(f"[{datetime.datetime.now()}] 会话ID: {process.headers.get('current_session_id', '未获取')}")
        
        if 'current_session_id' not in process.headers or not process.headers['current_session_id']:
            print(f"[{datetime.datetime.now()}] 错误: 未能获取会话ID，预约将失败")
            return False, f"预约失败: 未能获取会话ID"
        
        # 获取地图信息
        print(f"[{datetime.datetime.now()}] 获取地图信息: 经度={account.lng}, 纬度={account.lat}")
        try:
            p_c_map, source_data = process.get_map(lat=account.lat, lng=account.lng)
            
            if not p_c_map or len(p_c_map) == 0:
                print(f"[{datetime.datetime.now()}] 错误: 未能获取地图信息，预约将失败")
                return False, f"预约失败: 未能获取地图信息"
                
            print(f"[{datetime.datetime.now()}] 获取地图信息成功: 包含{len(p_c_map) if p_c_map else 0}个省份数据")
        except Exception as map_err:
            print(f"[{datetime.datetime.now()}] 错误: 获取地图信息失败: {str(map_err)}")
            return False, f"预约失败: 获取地图信息出错 - {str(map_err)}"

        # 获取该任务关联的所有商品
        item_mappings = TaskItemMapping.query.filter_by(task_id=task.id).all()

        # 如果没有找到映射，则使用任务自身的item_code（向后兼容）
        if not item_mappings:
            item_codes = [task.item_code]
        else:
            item_codes = [mapping.item_code for mapping in item_mappings]
        
        print(f"[{datetime.datetime.now()}] 准备预约商品: {item_codes}")
        
        # 记录预约结果
        all_success = True
        results = []
        
        # 遍历所有商品进行预约
        for item_code in item_codes:
            item_success = False
            item_message = "未知错误"
            item_name = item_code # 默认商品名称
            
            try:
                # 获取商品名称，优先使用ITEM_CONFIG中的配置
                if item_code in config.ITEM_CONFIG:
                    item_name = config.ITEM_CONFIG[item_code]['name']
                elif item_code in config.ITEM_MAP:
                    item_name = config.ITEM_MAP[item_code]
                
                print(f"[{datetime.datetime.now()}] 开始预约商品: {item_name}({item_code})")
                
                # 查找店铺ID
                print(f"[{datetime.datetime.now()}] 查找店铺ID: 省份={account.province}, 城市={account.city}")
                shop_id = process.get_location_count(
                    province=account.province,
                    city=account.city,
                    item_code=item_code,
                    p_c_map=p_c_map,
                    source_data=source_data,
                    lat=account.lat,
                    lng=account.lng
                )
                print(f"[{datetime.datetime.now()}] 找到店铺ID: {shop_id}")
                
                if not shop_id or shop_id == '0':
                    item_message = f"商品 {item_name}({item_code}) 未找到合适的预约店铺"
                    print(f"[{datetime.datetime.now()}] {item_message}")
                    results.append(f"{item_name}: 失败 ({item_message})")
                    all_success = False
                    continue # 跳过此商品的预约

                # 调用真实的预约接口
                print(f"[{datetime.datetime.now()}] 构建预约参数: shop_id={shop_id}, item_id={item_code}")
                params = process.act_params(shop_id, item_code)
                print(f"[{datetime.datetime.now()}] 预约参数: {params}")
                
                # 执行实际预约
                print(f"[{datetime.datetime.now()}] 执行预约请求")
                success, msg = process.reservation(params, mobile)
                print(f"[{datetime.datetime.now()}] 预约结果: 成功={success}, 消息={msg}")
                
                item_success = success
                item_message = msg if success else f"失败 ({msg})"
                
                # 更新任务最后运行时间 (仅当至少有一个商品成功或失败时更新)
                task.last_run = datetime.datetime.now()

                # 创建预约记录
                status = '成功' if success else '失败'
                reservation = Reservation(
                    user_id=task.user_id,
                    item_code=item_code,
                    status=status,
                    reserve_time=datetime.datetime.now(),
                    mt_account_id=task.mt_account_id
                )
                db.session.add(reservation)
                
                if not success:
                    all_success = False
                
                results.append(f"{item_name}: {status}")
                
            except Exception as item_e:
                item_message = f"商品 {item_name}({item_code}) 预约过程中出错: {str(item_e)}"
                print(f"[{datetime.datetime.now()}] {item_message}")
                # 记录失败结果
                results.append(f"{item_name}: 失败 ({item_message})")
                all_success = False
                
                # 即使单个商品失败，也尝试创建失败的预约记录
                try:
                    failed_reservation = Reservation(
                        user_id=task.user_id,
                        item_code=item_code,
                        status='失败',
                        reserve_time=datetime.datetime.now(),
                        mt_account_id=task.mt_account_id
                    )
                    db.session.add(failed_reservation)
                except Exception as db_err:
                    print(f"[{datetime.datetime.now()}] 记录失败预约时出错: {db_err}")

        db.session.commit()
        print(f"[{datetime.datetime.now()}] 数据库记录已提交")

        result_message = "，".join(results)
        message_title = "【成功】茅台预约" if all_success else "【部分成功/失败】茅台预约"

        # 构建推送内容
        user = User.query.get(task.user_id)
        username = user.username if user else "未知用户"
        formatted_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message_content = f"""
用户: {username}
预约时间: {formatted_time}
账号: {mobile[:3]}****{mobile[-4:]}
商品结果:
{chr(10).join(results)}
        """

        # 发送消息推送
        print(f"[{datetime.datetime.now()}] 发送消息推送")
        push_success = False
        if config.PUSH_TOKEN:
            print(f"[{datetime.datetime.now()}] 尝试通过PushPlus推送")
            push_success = send_message.send_pushplus(config.PUSH_TOKEN, message_title, message_content)
        if not push_success and config.DINGTALK_WEBHOOK:
            print(f"[{datetime.datetime.now()}] 尝试通过钉钉推送")
            send_message.send_webhook(config.DINGTALK_WEBHOOK, message_title, message_content)
        if config.SCKEY:
            print(f"[{datetime.datetime.now()}] 尝试通过ServerChan推送")
            send_message.send_server_chan(config.SCKEY, message_title, message_content)

        print(f"[{datetime.datetime.now()}] ==== 预约过程结束: 全部成功={all_success} ====\n")
        return all_success, f"预约结果: {result_message}"

    except Exception as e:
        # 记录更详细的错误日志
        import traceback
        print(f"[{datetime.datetime.now()}] real_reservation 函数出错: {e}")
        traceback.print_exc() 
        
        error_msg = f"预约过程出错: {str(e)}"
        # 发送错误消息推送
        push_success = False
        if config.PUSH_TOKEN:
            push_success = send_message.send_pushplus(config.PUSH_TOKEN, "【失败】茅台预约", error_msg)
        if not push_success and config.DINGTALK_WEBHOOK:
            send_message.send_webhook(config.DINGTALK_WEBHOOK, "【失败】茅台预约", error_msg)
        if config.SCKEY:
            send_message.send_server_chan(config.SCKEY, "【失败】茅台预约", error_msg)
            
        print(f"[{datetime.datetime.now()}] ==== 预约过程异常结束 ====\n")
        return False, error_msg

# 修改任务后台线程
def background_task_runner():
    """后台线程，自动执行预约任务"""
    print(f"\n\n[{datetime.datetime.now()}] ====== 后台任务线程已启动 ======\n\n")
    try:
        with app.app_context():
            while True:
                try:
                    now = datetime.datetime.now()
                    current_time = now.time()
                    
                    # 获取所有启用的任务
                    enabled_tasks = TaskSetting.query.filter_by(enabled=True).all()
                    if enabled_tasks:
                        print(f"[{now}] 当前时间: {current_time}, 检测到 {len(enabled_tasks)} 个启用的任务")
                    
                    for task in enabled_tasks:
                        # 检查账号是否可用
                        if not task.mt_account or not task.mt_account.is_active:
                            continue
                        
                        # 获取任务设定时间
                        task_time = task.preferred_time
                        
                        # 获取关联账号和商品信息用于日志
                        account_info = f"{task.mt_account.hidemobile}" if task.mt_account else "未知账号"
                        item_codes = [mapping.item_code for mapping in TaskItemMapping.query.filter_by(task_id=task.id).all()]
                        if not item_codes:
                            item_codes = [task.item_code]
                        
                        # 检查今天是否已经运行过
                        already_run_today = task.last_run is not None and task.last_run.date() == now.date()
                        
                        # 计算当前时间与任务时间的差距（分钟）
                        current_minutes = current_time.hour * 60 + current_time.minute
                        task_minutes = task_time.hour * 60 + task_time.minute
                        minutes_diff = abs(current_minutes - task_minutes)
                        
                        # 对每个任务进行报告，便于排查
                        print(f"[{now}] 任务ID={task.id}, 设定时间={task_time}, 当前分钟差={minutes_diff}, 今日已执行={already_run_today}")
                        
                        # 如果时间在1分钟内且今天还没有运行过
                        if minutes_diff <= 1 and not already_run_today:
                            print(f"\n[{now}] ===开始执行任务: ID={task.id}, 时间={task_time}, 账号={account_info}, 商品={item_codes}===\n")
                            success, message = real_reservation(task)
                            print(f"\n[{now}] ===任务执行结果: 成功={success}, 消息={message}===\n")
                            # 更新数据库
                            db.session.commit()
                    
                    # 每30秒检查一次任务
                    time.sleep(30)
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] 后台任务循环错误: {e}")
                    import traceback
                    traceback.print_exc()
                    # 错误后等待30秒再继续
                    time.sleep(30)
    except Exception as e:
        print(f"[{datetime.datetime.now()}] 后台任务线程严重错误: {e}")
        import traceback
        traceback.print_exc()

# 消息推送功能可以在预约成功后调用现有的推送服务
# 例如：send_message.send_pushplus(config.PUSH_TOKEN, '预约成功', '您的预约已成功')

def init_demo_data():
    """初始化演示数据"""
    try:
        # 检查是否已有用户数据
        if User.query.count() == 0:
            # 创建测试用户
            admin_user = User(username='admin')
            admin_user.set_password('admin123')
            demo_user = User(username='demo')
            demo_user.set_password('demo123')
            
            db.session.add(admin_user)
            db.session.add(demo_user)
            db.session.commit()
            
            # 为测试用户添加一些预约记录
            reservation1 = Reservation(
                user_id=demo_user.id,
                item_code='10941',
                status='成功',
                reserve_time=datetime.datetime.now() - datetime.timedelta(days=2)
            )
            
            reservation2 = Reservation(
                user_id=demo_user.id,
                item_code='10942',
                status='待处理',
            )
            
            reservation3 = Reservation(
                user_id=demo_user.id,
                item_code='10056',
                status='失败',
                reserve_time=datetime.datetime.now() - datetime.timedelta(days=1)
            )
            
            # 添加自动预约任务
            task1 = TaskSetting(
                user_id=demo_user.id,
                item_code='10941',
                enabled=True,
                preferred_time=datetime.time(9, 0)
            )
            
            db.session.add_all([reservation1, reservation2, reservation3, task1])
            db.session.commit()
            
            print("演示数据初始化完成!")
    except Exception as e:
        print(f"初始化演示数据出错: {e}")

@app.route('/profile')
@login_required
def profile():
    # 获取用户预约数据统计
    total_reservations = Reservation.query.filter_by(user_id=current_user.id).count()
    success_reservations = Reservation.query.filter_by(user_id=current_user.id, status='成功').count()
    pending_reservations = Reservation.query.filter_by(user_id=current_user.id, status='待处理').count()
    failed_reservations = Reservation.query.filter_by(user_id=current_user.id, status='失败').count()
    
    # 获取用户任务统计
    total_tasks = TaskSetting.query.filter_by(user_id=current_user.id).count()
    enabled_tasks = TaskSetting.query.filter_by(user_id=current_user.id, enabled=True).count()
    
    # 获取用户账号统计
    total_accounts = MaotaiAccount.query.filter_by(user_id=current_user.id).count()
    active_accounts = MaotaiAccount.query.filter_by(user_id=current_user.id, is_active=True).count()
    
    return render_template('profile.html', 
                          total_reservations=total_reservations,
                          success_reservations=success_reservations,
                          pending_reservations=pending_reservations,
                          failed_reservations=failed_reservations,
                          total_tasks=total_tasks,
                          enabled_tasks=enabled_tasks,
                          total_accounts=total_accounts,
                          active_accounts=active_accounts)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('密码已成功修改!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('当前密码不正确!', 'danger')
    return render_template('change_password.html', form=form)

class MaotaiAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mobile = db.Column(db.String(128), nullable=False)  # 加密后的手机号
    hidemobile = db.Column(db.String(20), nullable=False)  # 部分隐藏的手机号，用于显示
    province = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(20), nullable=False)
    lat = db.Column(db.String(20), nullable=False)
    lng = db.Column(db.String(20), nullable=False)
    token = db.Column(db.String(128), nullable=False)
    userid = db.Column(db.String(128), nullable=False)  # 加密后的userid
    enddate = db.Column(db.String(20), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)
    last_use = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class MaotaiAccountForm(FlaskForm):
    mobile = StringField('手机号', validators=[DataRequired(), Regexp(r'^1[3-9]\d{9}$', message='请输入正确格式的手机号')])
    province = StringField('省份', validators=[DataRequired()])
    city = StringField('城市', validators=[DataRequired()])
    lat = StringField('纬度')
    lng = StringField('经度')
    location = StringField('位置信息', validators=[DataRequired()])
    token = StringField('Token')
    userid = StringField('用户ID')
    enddate = StringField('预约截止日期', default='99999999')
    submit = SubmitField('保存账号')

class VerificationForm(FlaskForm):
    mobile = HiddenField('手机号')
    code = StringField('验证码', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('验证')

class LocationSearchForm(FlaskForm):
    query = StringField('位置搜索', validators=[DataRequired()])
    submit = SubmitField('搜索')

@app.route('/accounts')
@login_required
def accounts():
    user_accounts = MaotaiAccount.query.filter_by(user_id=current_user.id).all()
    return render_template('accounts.html', accounts=user_accounts)

@app.route('/add_account', methods=['GET', 'POST'])
@login_required
def add_account():
    form = MaotaiAccountForm()
    
    if form.validate_on_submit():
        # 初始化AES密钥
        aes_key = privateCrypt.get_aes_key()
        
        # 加密手机号和用户ID
        encrypt_mobile = privateCrypt.encrypt_aes_ecb(form.mobile.data, aes_key)
        encrypt_userid = privateCrypt.encrypt_aes_ecb(form.userid.data, aes_key)
        
        # 隐藏部分手机号
        hide_mobile = form.mobile.data.replace(form.mobile.data[3:7], '****')
        
        # 创建新账号
        account = MaotaiAccount(
            user_id=current_user.id,
            mobile=encrypt_mobile,
            hidemobile=hide_mobile,
            province=form.province.data,
            city=form.city.data,
            lat=form.lat.data,
            lng=form.lng.data,
            token=form.token.data,
            userid=encrypt_userid,
            enddate=form.enddate.data
        )
        
        db.session.add(account)
        db.session.commit()
        
        flash('茅台账号添加成功！', 'success')
        return redirect(url_for('accounts'))
    
    return render_template('add_account.html', form=form)

@app.route('/search_location', methods=['POST'])
@login_required
def search_location():
    query = request.form.get('query', '')
    if not query:
        return jsonify({'error': '请输入位置关键词'}), 400
    
    try:
        # 初始化headers确保API可以正常调用
        process.init_headers()
        # 调用process模块搜索位置
        results = process.select_geo(query)
        return jsonify({
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_verification_code', methods=['POST'])
@login_required
def get_verification_code():
    mobile = request.form.get('mobile', '')
    if not mobile or not mobile.isdigit() or len(mobile) != 11:
        return jsonify({'error': '请输入正确的手机号'}), 400
    
    try:
        # 初始化headers确保API可以正常调用
        process.init_headers()
        # 调用process模块发送验证码
        result = process.get_vcode(mobile)
        return jsonify({'success': True, 'message': '验证码已发送'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verify_code', methods=['POST'])
@login_required
def verify_code():
    mobile = request.form.get('mobile', '')
    code = request.form.get('code', '')
    
    if not mobile or not code:
        return jsonify({'error': '请输入手机号和验证码'}), 400
    
    try:
        # 初始化headers确保API可以正常调用
        process.init_headers()
        # 调用process模块验证登录
        token, userid = process.login(mobile, code)
        
        return jsonify({
            'success': True,
            'token': token,
            'userid': userid
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/edit_account/<int:account_id>', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    account = MaotaiAccount.query.get_or_404(account_id)
    
    # 确认账号归属当前用户
    if account.user_id != current_user.id:
        flash('您无权编辑此账号！', 'danger')
        return redirect(url_for('accounts'))
    
    # 初始化AES密钥
    aes_key = privateCrypt.get_aes_key()
    
    # 解密手机号和用户ID以显示在表单中
    try:
        decrypted_mobile = privateCrypt.decrypt_aes_ecb(account.mobile, aes_key)
        decrypted_userid = privateCrypt.decrypt_aes_ecb(account.userid, aes_key)
    except:
        decrypted_mobile = ''
        decrypted_userid = ''
    
    form = MaotaiAccountForm(obj=account)
    form.mobile.data = decrypted_mobile
    form.userid.data = decrypted_userid
    
    if form.validate_on_submit():
        # 加密手机号和用户ID
        encrypt_mobile = privateCrypt.encrypt_aes_ecb(form.mobile.data, aes_key)
        encrypt_userid = privateCrypt.encrypt_aes_ecb(form.userid.data, aes_key)
        
        # 隐藏部分手机号
        hide_mobile = form.mobile.data.replace(form.mobile.data[3:7], '****')
        
        # 更新账号信息
        account.mobile = encrypt_mobile
        account.hidemobile = hide_mobile
        account.province = form.province.data
        account.city = form.city.data
        account.lat = form.lat.data
        account.lng = form.lng.data
        account.token = form.token.data
        account.userid = encrypt_userid
        account.enddate = form.enddate.data
        
        db.session.commit()
        
        flash('账号信息已更新！', 'success')
        return redirect(url_for('accounts'))
    
    return render_template('edit_account.html', form=form, account=account)

@app.route('/delete_account/<int:account_id>', methods=['POST'])
@login_required
def delete_account(account_id):
    account = MaotaiAccount.query.get_or_404(account_id)
    
    # 确认账号归属当前用户
    if account.user_id != current_user.id:
        flash('您无权删除此账号！', 'danger')
        return redirect(url_for('accounts'))
    
    db.session.delete(account)
    db.session.commit()
    
    flash('账号已删除！', 'success')
    return redirect(url_for('accounts'))

@app.route('/search_location_mock', methods=['POST'])
@login_required
def search_location_mock():
    query = request.form.get('query', '')
    if not query:
        return jsonify({'error': '请输入搜索关键词'}), 400
    
    # 模拟地理位置搜索结果
    mock_results = [
        {
            'formatted_address': f'{query}附近的小区A',
            'province': '北京市',
            'city': '北京市',
            'district': '朝阳区',
            'location': '116.481488,39.990464'
        },
        {
            'formatted_address': f'{query}附近的小区B',
            'province': '北京市',
            'city': '北京市',
            'district': '海淀区',
            'location': '116.307487,40.058209'
        },
        {
            'formatted_address': f'{query}周边商业中心',
            'province': '北京市',
            'city': '北京市',
            'district': '东城区',
            'location': '116.416357,39.928353'
        }
    ]
    return jsonify({'results': mock_results})

@app.route('/get_verification_code_mock', methods=['POST'])
@login_required
def get_verification_code_mock():
    mobile = request.form.get('mobile', '')
    if not mobile or not mobile.isdigit() or len(mobile) != 11:
        return jsonify({'error': '请输入正确的手机号'}), 400
    
    # 模拟发送验证码，实际上不会发送
    return jsonify({'success': True, 'message': '验证码已发送（模拟）'})

@app.route('/verify_code_mock', methods=['POST'])
@login_required
def verify_code_mock():
    mobile = request.form.get('mobile', '')
    code = request.form.get('code', '')
    
    if not mobile or not code:
        return jsonify({'error': '请输入手机号和验证码'}), 400
    
    # 模拟验证过程，任何验证码都认为是正确的
    if len(code) != 6:
        return jsonify({'error': '验证码格式不正确'}), 400
    
    # 返回模拟的token和userid
    return jsonify({
        'success': True,
        'token': f'mock_token_{int(time.time())}',
        'userid': f'user_{mobile[-4:]}'
    })

@app.route('/system_config', methods=['GET', 'POST'])
@login_required
def system_config():
    # 只允许管理员访问（这里简单定义admin或id为1的用户为管理员）
    if current_user.username != 'admin' and current_user.id != 1:
        flash('您无权访问此页面', 'danger')
        return redirect(url_for('home'))
    
    # 读取当前.env文件内容
    env_file_path = '.env'
    env_vars = {}
    try:
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # 去除引号
                        value = value.strip().strip("'").strip('"')
                        env_vars[key.strip()] = value
    except Exception as e:
        flash(f'读取环境变量文件失败: {str(e)}', 'danger')
    
    if request.method == 'POST':
        # 处理表单提交
        try:
            env_vars = {}
            # 获取所有表单字段
            for key, value in request.form.items():
                if key.startswith('env_key_'):
                    index = key.replace('env_key_', '')
                    env_key = request.form.get(f'env_key_{index}')
                    env_value = request.form.get(f'env_value_{index}')
                    
                    if env_key and env_key not in env_vars:  # 确保没有重复的键
                        env_vars[env_key] = env_value
            
            # 写入.env文件
            with open(env_file_path, 'w', encoding='utf-8') as f:
                for key, value in env_vars.items():
                    f.write(f"{key}='{value}'\n")
            
            # 重新加载环境变量
            load_dotenv(override=True)
            
            # 更新配置中的值
            config.PUSH_TOKEN = os.getenv('PUSHPLUS_KEY', '')
            config.SCKEY = os.environ.get('SCKEY')
            config.DINGTALK_WEBHOOK = os.environ.get('DINGTALK_WEBHOOK')
            config.AMAP_KEY = os.environ.get('GAODE_KEY')
            config.PRIVATE_AES_KEY = os.environ.get('PRIVATE_AES_KEY')
            
            flash('环境变量已更新', 'success')
            return redirect(url_for('system_config'))
        except Exception as e:
            flash(f'更新环境变量失败: {str(e)}', 'danger')
    
    return render_template('system_config.html', env_vars=env_vars)

@app.context_processor
def inject_config():
    """将config配置注入到所有模板中"""
    return dict(config=config)

# 用户推送设置模型
class UserPushSetting(db.Model):
    """用户推送设置"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # 是否启用系统推送
    enable_push = db.Column(db.Boolean, default=False)
    
    # PushPlus配置
    pushplus_token = db.Column(db.String(50), nullable=True)
    
    # Server酱配置
    serverchan_token = db.Column(db.String(50), nullable=True)
    
    # 钉钉机器人配置
    dingtalk_webhook = db.Column(db.String(255), nullable=True)
    
    # 创建时间
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)
    # 更新时间
    update_time = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    def __repr__(self):
        return f'<UserPushSetting {self.id}>'

# 用户推送设置表单
class UserPushSettingForm(FlaskForm):
    """用户推送设置表单"""
    enable_push = BooleanField('启用系统消息推送', default=False)
    
    # PushPlus配置
    pushplus_token = StringField('PushPlus Token', 
                                validators=[Optional(), Length(max=50)],
                                render_kw={"placeholder": "请输入PushPlus的token"})
    
    # Server酱配置
    serverchan_token = StringField('Server酱 SendKey', 
                                validators=[Optional(), Length(max=50)],
                                render_kw={"placeholder": "请输入Server酱的SendKey"})
    
    # 钉钉机器人配置
    dingtalk_webhook = StringField('钉钉机器人 Webhook', 
                                validators=[Optional(), Length(max=255)],
                                render_kw={"placeholder": "请输入钉钉机器人的Webhook地址"})
    
    submit = SubmitField('保存设置')

@app.route('/push_settings', methods=['GET', 'POST'])
@login_required
def push_settings():
    # 获取当前用户的推送设置，如果不存在则创建
    push_setting = UserPushSetting.query.filter_by(user_id=current_user.id).first()
    if not push_setting:
        push_setting = UserPushSetting(user_id=current_user.id)
        db.session.add(push_setting)
        db.session.commit()
    
    # 创建表单并预填充现有设置
    form = UserPushSettingForm(obj=push_setting)
    
    # 处理表单提交
    if form.validate_on_submit():
        form.populate_obj(push_setting)
        db.session.commit()
        flash('推送设置已更新', 'success')
        return redirect(url_for('push_settings'))
    
    return render_template('push_settings.html', form=form)

@app.route('/test_push', methods=['POST'])
@login_required
def test_push():
    push_type = request.form.get('push_type')
    push_setting = UserPushSetting.query.filter_by(user_id=current_user.id).first()
    
    if not push_setting:
        return jsonify({'success': False, 'message': '未找到推送设置'})
    
    # 测试消息内容
    title = 'iMaoTai 测试消息'
    content = f'这是一条来自iMaoTai的测试消息，发送时间：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    
    success = False
    message = ''
    
    try:
        # 根据推送类型调用不同的推送方法
        if push_type == 'pushplus':
            if not push_setting.pushplus_token:
                return jsonify({'success': False, 'message': '请先设置PushPlus Token'})
            
            # 调用PushPlus推送
            response = requests.post(
                'http://www.pushplus.plus/send',
                json={
                    'token': push_setting.pushplus_token,
                    'title': title,
                    'content': content,
                    'template': 'html'
                }
            )
            
            result = response.json()
            if result.get('code') == 200:
                success = True
                message = 'PushPlus推送成功'
            else:
                message = f'PushPlus推送失败: {result.get("msg")}'
                
        elif push_type == 'serverchan':
            if not push_setting.serverchan_token:
                return jsonify({'success': False, 'message': '请先设置Server酱SendKey'})
            
            # 调用Server酱推送
            response = requests.post(
                f'https://sctapi.ftqq.com/{push_setting.serverchan_token}.send',
                data={
                    'title': title,
                    'desp': content
                }
            )
            
            result = response.json()
            if result.get('code') == 0:
                success = True
                message = 'Server酱推送成功'
            else:
                message = f'Server酱推送失败: {result.get("message")}'
                
        elif push_type == 'dingtalk':
            if not push_setting.dingtalk_webhook:
                return jsonify({'success': False, 'message': '请先设置钉钉机器人Webhook'})
            
            # 调用钉钉机器人推送
            response = requests.post(
                push_setting.dingtalk_webhook,
                json={
                    'msgtype': 'text',
                    'text': {
                        'content': f'{title}\n\n{content}'
                    }
                }
            )
            
            result = response.json()
            if result.get('errcode') == 0:
                success = True
                message = '钉钉机器人推送成功'
            else:
                message = f'钉钉机器人推送失败: {result.get("errmsg")}'
        else:
            message = '未知的推送类型'
            
    except Exception as e:
        message = f'推送失败: {str(e)}'
        
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/get_products', methods=['GET'])
@login_required
def get_products():
    """获取可预约的商品列表API"""
    try:
        # 使用CommodityFetcher类直接获取商品列表
        fetcher = CommodityFetcher()
        products = fetcher.fetch_commodities()
        
        if products:
            # 存储sessionId到会话中，后续获取店铺列表时使用
            session['mt_session_id'] = fetcher.session_id
            
            # 转换为前端需要的格式
            items = []
            for product in products:
                item = {
                    'itemId': product['Code'],
                    'itemCode': product['Code'],
                    'title': product['Title'],
                    'content': product['Description'],
                    'price': product['Price']
                }
                items.append(item)
            
            return jsonify({
                'success': True,
                'items': items
            })
        else:
            return jsonify({
                'success': False,
                'message': '获取商品列表失败，返回了空列表'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取商品列表失败: {str(e)}'
        })

@app.route('/api/get_shops', methods=['GET'])
@login_required
def get_shops():
    """获取指定商品的可预约店铺列表API"""
    try:
        # 初始化headers
        process.init_headers()
        
        item_id = request.args.get('item_id')
        if not item_id:
            return jsonify({
                'success': False,
                'message': '缺少商品ID参数'
            })
            
        # 获取会话ID
        session_id = session.get('mt_session_id')
        if not session_id:
            # 如果没有会话ID，重新获取商品列表
            product_result = process.get_product_list()
            if not product_result['success']:
                return jsonify({
                    'success': False,
                    'message': '获取会话ID失败'
                })
            session_id = product_result['session_id']
            session['mt_session_id'] = session_id
        
        # 获取当前用户的茅台账号，用于确定省份
        account = MaotaiAccount.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not account:
            return jsonify({
                'success': False,
                'message': '请先添加茅台账号'
            })
            
        # 获取指定省份的店铺列表
        result = process.get_shop_list(session_id, account.province, item_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'shops': result['shops']
            })
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取店铺列表失败: {str(e)}'
        })

@app.route('/api/find_nearest_shop', methods=['POST'])
@login_required
def find_nearest_shop():
    """查找最近的店铺API"""
    try:
        # 初始化headers
        process.init_headers()
        
        data = request.json
        item_id = data.get('item_id')
        lat = data.get('lat')
        lng = data.get('lng')
        
        if not item_id or not lat or not lng:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            })
        
        # 获取会话ID
        session_id = session.get('mt_session_id')
        if not session_id:
            # 如果没有会话ID，重新获取商品列表
            product_result = process.get_product_list()
            if not product_result['success']:
                return jsonify({
                    'success': False,
                    'message': '获取会话ID失败'
                })
            session_id = product_result['session_id']
            session['mt_session_id'] = session_id
        
        # 获取当前用户的茅台账号，用于确定省份
        account = MaotaiAccount.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not account:
            return jsonify({
                'success': False,
                'message': '请先添加茅台账号'
            })
            
        # 获取指定省份的店铺列表
        shop_result = process.get_shop_list(session_id, account.province, item_id)
        
        if not shop_result['success']:
            return jsonify({
                'success': False,
                'message': shop_result['message']
            })
            
        # 查找最近的店铺
        p_c_map, shop_data = process.get_map(account.lat, account.lng)
        shop_id = process.distance_shop(account.city, item_id, p_c_map, account.province, shop_result['shops'], shop_data, account.lat, account.lng)
        
        if shop_id:
            return jsonify({
                'success': True,
                'shop_id': shop_id
            })
        else:
            return jsonify({
                'success': False,
                'message': '未找到合适的店铺'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'查找最近店铺失败: {str(e)}'
        })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_demo_data()
    
    try:
        # 启动后台任务线程
        scheduler_thread = threading.Thread(target=background_task_runner, daemon=True)
        scheduler_thread.start()
        print(f"[{datetime.datetime.now()}] 后台任务线程已启动")
        
        app.run(debug=True, use_reloader=False)  # 禁用reloader避免线程重复启动
    except Exception as e:
        print(f"应用启动错误: {e}")
        import traceback
        traceback.print_exc() 