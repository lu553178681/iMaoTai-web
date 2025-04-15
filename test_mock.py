#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import time
import sys

# 测试服务器地址
BASE_URL = "http://localhost:5000"  # 根据实际情况修改端口

# 测试账号
TEST_MOBILE = "13800138000"
TEST_CODE = "123456"
TEST_LOCATION = "北京市海淀区"

# 测试颜色输出
def print_color(text, color):
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

# 登录系统（如果需要）
def login():
    print_color("尝试登录系统...", "yellow")
    # 此处需要根据实际系统情况实现
    return None

# 测试获取验证码
def test_get_verification_code():
    print_color("\n测试获取验证码...", "yellow")
    try:
        response = requests.post(
            f"{BASE_URL}/get_verification_code_mock",
            data={"mobile": TEST_MOBILE},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print_color(f"成功: {result.get('message', '')}", "green")
                return True
            else:
                print_color(f"失败: {result.get('error', '未知错误')}", "red")
                return False
        else:
            print_color(f"HTTP错误: {response.status_code}", "red")
            return False
    except Exception as e:
        print_color(f"异常: {str(e)}", "red")
        return False

# 测试验证码验证
def test_verify_code():
    print_color("\n测试验证码验证...", "yellow")
    try:
        response = requests.post(
            f"{BASE_URL}/verify_code_mock",
            data={"mobile": TEST_MOBILE, "code": TEST_CODE},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print_color(f"成功: token={result.get('token', '')}, userid={result.get('userid', '')}", "green")
                return True
            else:
                print_color(f"失败: {result.get('error', '未知错误')}", "red")
                return False
        else:
            print_color(f"HTTP错误: {response.status_code}", "red")
            return False
    except Exception as e:
        print_color(f"异常: {str(e)}", "red")
        return False

# 测试位置搜索
def test_search_location():
    print_color("\n测试位置搜索...", "yellow")
    try:
        response = requests.post(
            f"{BASE_URL}/search_location_mock",
            data={"query": TEST_LOCATION},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if "results" in result:
                locations = result.get("results", [])
                print_color(f"成功: 找到 {len(locations)} 个位置", "green")
                for i, loc in enumerate(locations):
                    print_color(f"  {i+1}. {loc.get('formatted_address')} ({loc.get('province')}, {loc.get('city')})", "green")
                return True
            else:
                print_color(f"失败: {result.get('error', '未知错误')}", "red")
                return False
        else:
            print_color(f"HTTP错误: {response.status_code}", "red")
            return False
    except Exception as e:
        print_color(f"异常: {str(e)}", "red")
        return False

def main():
    print_color("开始测试模拟API...", "yellow")
    
    # 测试获取验证码
    if not test_get_verification_code():
        print_color("验证码获取测试失败，中止测试", "red")
        return
    
    # 测试验证码验证
    if not test_verify_code():
        print_color("验证码验证测试失败，中止测试", "red")
        return
    
    # 测试位置搜索
    if not test_search_location():
        print_color("位置搜索测试失败，中止测试", "red")
        return
    
    print_color("\n所有测试完成!", "green")

if __name__ == "__main__":
    main() 