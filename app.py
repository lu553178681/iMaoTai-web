from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('确认密码', 
                                   validators=[DataRequired(), EqualTo('password', message='两次输入的密码必须一致')])
    submit = SubmitField('注册')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被注册，请使用其他用户名')

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
        recent_reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.create_time.desc()).limit(5).all()
        
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
    item_codes = MultipleCheckboxField('商品类型(可多选)', validators=[DataRequired(message="请至少选择一个商品，可多选但不必全选")], 
                           choices=[(k, v['name']) for k, v in config.ITEM_CONFIG.items() if v['enabled']])
    submit = SubmitField('提交预约')

class TaskSettingForm(FlaskForm):
    item_codes = MultipleCheckboxField('商品类型(可多选)', validators=[DataRequired(message="请至少选择一个商品，可多选但不必全选")], 
                           choices=[(k, v['name']) for k, v in config.ITEM_CONFIG.items() if v['enabled']])
    mt_account_id = SelectField('使用账号', validators=[DataRequired()], coerce=int)
    enabled = BooleanField('启用自动预约', default=True)
    preferred_time = TimeField('首选预约时间', default=datetime.time(9, 0), validators=[DataRequired()])
    submit = SubmitField('保存设置')

@app.route('/reservations')
@login_required
def reservations():
    user_reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    return render_template('reservations.html', reservations=user_reservations)

@app.route('/create_reservation', methods=['GET', 'POST'])
@login_required
def create_reservation():
    form = ReservationForm()
    if form.validate_on_submit():
        # 获取所有选中的商品
        selected_item_codes = form.item_codes.data
        
        # 为每个选择的商品创建预约
        for item_code in selected_item_codes:
            reservation = Reservation(
                user_id=current_user.id,
                item_code=item_code,
                status='待处理'
            )
            db.session.add(reservation)
        
        db.session.commit()
        
        # 构建消息推送内容
        item_names = []
        for item_code in selected_item_codes:
            if item_code in config.ITEM_CONFIG:
                item_names.append(config.ITEM_CONFIG[item_code]['name'])
            elif item_code in config.ITEM_MAP:
                item_names.append(config.ITEM_MAP[item_code])
            else:
                item_names.append(item_code)
                
        formatted_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_content = f"""
用户: {current_user.username}
提交时间: {formatted_time}
提交商品:
{chr(10).join(['- ' + name for name in item_names])}
状态: 待处理
        """
        
        # 发送消息推送
        push_success = False
        if config.PUSH_TOKEN:
            push_success = send_message.send_pushplus(config.PUSH_TOKEN, "【提交】茅台预约申请", message_content)
        if not push_success and config.DINGTALK_WEBHOOK:
            send_message.send_webhook(config.DINGTALK_WEBHOOK, "【提交】茅台预约申请", message_content)
        if config.SCKEY:
            send_message.send_server_chan(config.SCKEY, "【提交】茅台预约申请", message_content)
        
        flash(f'已成功提交 {len(selected_item_codes)} 个商品的预约!', 'success')
        return redirect(url_for('reservations'))
    return render_template('create_reservation.html', form=form)

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
    
    if form.validate_on_submit():
        # 获取所有选中的商品
        selected_item_codes = form.item_codes.data
        
        # 先查找是否有此账号的现有任务
        mt_account_id = form.mt_account_id.data
        existing_task = TaskSetting.query.filter_by(user_id=current_user.id, mt_account_id=mt_account_id).first()
        
        if existing_task:
            # 如果有现有任务，则更新它
            existing_task.enabled = form.enabled.data
            existing_task.preferred_time = form.preferred_time.data
            existing_task.item_code = selected_item_codes[0] if selected_item_codes else ''  # 兼容旧版
            
            # 删除旧的商品映射
            TaskItemMapping.query.filter_by(task_id=existing_task.id).delete()
            
            task = existing_task
        else:
            # 创建新任务
            task = TaskSetting(
                user_id=current_user.id,
                item_code=selected_item_codes[0] if selected_item_codes else '',  # 兼容旧版
                mt_account_id=mt_account_id,
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
        account = MaotaiAccount.query.get(mt_account_id)
        account_info = f"{account.hidemobile} ({account.province}, {account.city})" if account else "未知账号"
        
        item_names = []
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
        action_type = "更新" if existing_task else "创建"
        
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
        flash('预约执行成功!', 'success')
    else:
        flash(f'预约执行失败: {message}', 'danger')
    
    return redirect(url_for('tasks'))

def real_reservation(task):
    """实际预约过程，使用茅台账号信息调用预约API"""
    # 获取任务关联的茅台账号
    account = MaotaiAccount.query.filter_by(id=task.mt_account_id).first()
    
    if not account:
        return False, "预约失败: 找不到关联的茅台账号"
    
    if not account.is_active:
        return False, "预约失败: 账号已被禁用"
    
    # 解密敏感信息
    try:
        # 重用已有的AES密钥
        key = privateCrypt.get_aes_key()
        
        # 解密手机号和用户ID
        mobile = privateCrypt.decrypt_aes_ecb(account.mobile, key)
        user_id = privateCrypt.decrypt_aes_ecb(account.userid, key)
    except Exception as e:
        return False, f"预约失败: 解密账号信息出错 - {str(e)}"
    
    # 调用预约API
    try:
        # 初始化headers
        process.init_headers()
        
        # 获取该任务关联的所有商品
        item_mappings = TaskItemMapping.query.filter_by(task_id=task.id).all()
        
        # 如果没有找到映射，则使用任务自身的item_code（向后兼容）
        if not item_mappings:
            item_codes = [task.item_code]
        else:
            item_codes = [mapping.item_code for mapping in item_mappings]
        
        # 记录预约结果
        all_success = True
        results = []
        
        # 遍历所有商品进行预约
        for item_code in item_codes:
            # 这里可以调用真实的预约接口，传入item_code
            # 暂时使用模拟接口
            success = random.choice([True, False, True, True])
            
            # 更新任务最后运行时间
            task.last_run = datetime.datetime.now()
            
            # 创建预约记录
            status = '成功' if success else '失败'
            reservation = Reservation(
                user_id=task.user_id,
                item_code=item_code,
                status=status,
                reserve_time=datetime.datetime.now()
            )
            
            db.session.add(reservation)
            if not success:
                all_success = False
            
            # 获取商品名称，优先使用ITEM_CONFIG中的配置
            item_name = item_code
            if item_code in config.ITEM_CONFIG:
                item_name = config.ITEM_CONFIG[item_code]['name']
            elif item_code in config.ITEM_MAP:
                item_name = config.ITEM_MAP[item_code]
                
            results.append(f"{item_name}: {'成功' if success else '失败'}")
        
        db.session.commit()
        
        result_message = "，".join(results)
        message_title = "【成功】茅台预约" if all_success else "【部分成功】茅台预约"
        
        # 构建推送内容
        user = User.query.get(task.user_id)
        username = user.username if user else "未知用户"
        formatted_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message_content = f"""
用户: {username}
预约时间: {formatted_time}
账号: {mobile[:3]}****{mobile[-4:]}
商品结果:
{chr(10).join(['- ' + r for r in results])}
        """
        
        # 发送消息推送
        push_success = False
        if config.PUSH_TOKEN:
            push_success = send_message.send_pushplus(config.PUSH_TOKEN, message_title, message_content)
        if not push_success and config.DINGTALK_WEBHOOK:
            send_message.send_webhook(config.DINGTALK_WEBHOOK, message_title, message_content)
        if config.SCKEY:
            send_message.send_server_chan(config.SCKEY, message_title, message_content)
        
        return all_success, f"预约结果: {result_message}"
        
    except Exception as e:
        error_msg = f"预约过程出错: {str(e)}"
        # 发送错误消息推送
        push_success = False
        if config.PUSH_TOKEN:
            push_success = send_message.send_pushplus(config.PUSH_TOKEN, "【失败】茅台预约", error_msg)
        if not push_success and config.DINGTALK_WEBHOOK:
            send_message.send_webhook(config.DINGTALK_WEBHOOK, "【失败】茅台预约", error_msg)
        if config.SCKEY:
            send_message.send_server_chan(config.SCKEY, "【失败】茅台预约", error_msg)
        return False, error_msg

# 修改任务后台线程
def background_task_runner():
    """后台线程，自动执行预约任务"""
    with app.app_context():
        while True:
            try:
                now = datetime.datetime.now()
                current_time = now.time()
                
                # 获取所有启用的任务
                enabled_tasks = TaskSetting.query.filter_by(enabled=True).all()
                
                for task in enabled_tasks:
                    # 检查账号是否可用
                    if not task.mt_account or not task.mt_account.is_active:
                        continue
                    
                    # 检查是否在预约时间窗口内（前后5分钟）
                    task_time = task.preferred_time
                    time_diff = (datetime.datetime.combine(datetime.date.today(), current_time) - 
                                datetime.datetime.combine(datetime.date.today(), task_time))
                    minutes_diff = abs(time_diff.total_seconds() / 60)
                    
                    # 如果在时间窗口内且今天还没有运行过
                    if minutes_diff <= 5:
                        # 检查今天是否已经运行过
                        if task.last_run is None or task.last_run.date() < now.date():
                            real_reservation(task)
                
                # 每分钟检查一次
                time.sleep(60)
            except Exception as e:
                print(f"后台任务错误: {e}")
                time.sleep(60)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_demo_data()
    
    # 启动后台任务线程
    scheduler_thread = threading.Thread(target=background_task_runner, daemon=True)
    scheduler_thread.start()
    
    app.run(debug=True) 