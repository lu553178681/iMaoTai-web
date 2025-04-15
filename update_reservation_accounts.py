#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import app, db, Reservation, TaskSetting, MaotaiAccount
import datetime

def update_reservation_accounts():
    """为现有预约记录关联对应的茅台账号"""
    try:
        # 获取所有没有关联账号的预约记录
        reservations = Reservation.query.filter_by(mt_account_id=None).all()
        print(f"找到 {len(reservations)} 条未关联账号的预约记录")
        
        # 获取所有自动任务，用于匹配账号
        tasks = TaskSetting.query.all()
        print(f"可用于匹配的任务数量: {len(tasks)}")
        
        # 获取所有茅台账号
        accounts = MaotaiAccount.query.all()
        print(f"可用的茅台账号数量: {len(accounts)}")
        
        # 如果用户只有一个账号，使用该账号关联所有预约
        user_accounts = {}
        
        # 按用户ID分组统计账号
        for account in accounts:
            if account.user_id not in user_accounts:
                user_accounts[account.user_id] = []
            user_accounts[account.user_id].append(account)
        
        updated_count = 0
        
        for reservation in reservations:
            account_id = None
            
            # 尝试通过创建时间匹配最近的任务
            matched_task = None
            min_time_diff = datetime.timedelta(days=365)  # 初始设置为一年
            
            for task in tasks:
                if task.user_id == reservation.user_id and task.item_code == reservation.item_code:
                    if task.last_run and reservation.reserve_time:
                        time_diff = abs(task.last_run - reservation.reserve_time)
                        if time_diff < min_time_diff:
                            min_time_diff = time_diff
                            matched_task = task
            
            # 如果找到匹配的任务，使用其账号
            if matched_task and matched_task.mt_account_id:
                account_id = matched_task.mt_account_id
                print(f"通过任务匹配到账号 ID: {account_id} 用于预约 ID: {reservation.id}")
            # 如果用户只有一个账号，直接使用
            elif reservation.user_id in user_accounts and len(user_accounts[reservation.user_id]) == 1:
                account_id = user_accounts[reservation.user_id][0].id
                print(f"通过用户唯一账号匹配到账号 ID: {account_id} 用于预约 ID: {reservation.id}")
            
            # 更新预约记录
            if account_id:
                reservation.mt_account_id = account_id
                updated_count += 1
        
        # 提交更改
        db.session.commit()
        print(f"成功更新 {updated_count} 条预约记录")
        
        return True
    except Exception as e:
        print(f"更新预约记录账号关联时出错: {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    with app.app_context():
        update_reservation_accounts() 