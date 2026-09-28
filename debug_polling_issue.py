#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试轮询问题的详细版本
"""
import os

def get_account_last_type_index(account_name):
    """获取账号内标题类型轮询的最后一次索引"""
    index_file = os.path.join(os.getcwd(), f'account_type_index_{account_name}.txt')
    try:
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                result = int(f.read().strip())
                print(f"📖 读取账号 {account_name} 类型索引: {result}")
                return result
    except Exception as e:
        print(f"❌ 读取账号 {account_name} 类型索引失败: {e}")
    print(f"📖 账号 {account_name} 没有索引文件，返回默认值 0")
    return 0

def save_account_type_index(account_name, index):
    """保存账号内标题类型轮询索引"""
    index_file = os.path.join(os.getcwd(), f'account_type_index_{account_name}.txt')
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(str(index))
        print(f"💾 保存账号 {account_name} 类型索引: {index}")
        return True
    except Exception as e:
        print(f"❌ 保存账号 {account_name} 类型索引失败: {e}")
        return False

def debug_polling_logic(account_name, available_title_types, rounds=10):
    """调试轮询逻辑"""
    print(f"\n=== 调试账号 {account_name} 的轮询逻辑 ===")
    print(f"可用标题类型: {available_title_types}")
    print(f"类型总数: {len(available_title_types)}")
    print()
    
    # 清空之前的索引文件
    index_file = os.path.join(os.getcwd(), f'account_type_index_{account_name}.txt')
    if os.path.exists(index_file):
        os.remove(index_file)
        print(f"🗑️ 删除旧的索引文件")
    
    selected_types = []
    
    for round_num in range(1, rounds + 1):
        print(f"--- 第 {round_num} 轮 ---")
        
        # 1. 获取当前类型索引
        current_type_index = get_account_last_type_index(account_name)
        print(f"📍 当前类型索引: {current_type_index}")
        
        # 2. 计算选择的类型
        modulo_calc = current_type_index % len(available_title_types)
        selected_type = available_title_types[modulo_calc]
        print(f"🔢 模运算: {current_type_index} % {len(available_title_types)} = {modulo_calc}")
        print(f"✅ 选择类型: {selected_type}")
        selected_types.append(selected_type)
        
        # 3. 计算并保存下一个索引
        next_type_index = current_type_index + 1
        print(f"➡️ 下一个原始索引: {next_type_index}")
        save_account_type_index(account_name, next_type_index)
        print()
    
    print(f"📊 总结 (共 {rounds} 轮):")
    print(f"选择的类型序列: {selected_types}")
    
    # 统计每种类型被选择的次数
    type_count = {}
    for t in selected_types:
        type_count[t] = type_count.get(t, 0) + 1
    
    print(f"类型使用统计:")
    for t in sorted(type_count.keys()):
        print(f"  类型 {t}: {type_count[t]} 次")
    
    # 检查是否所有类型都被使用
    unused_types = [t for t in available_title_types if t not in type_count]
    if unused_types:
        print(f"⚠️ 未使用的类型: {unused_types}")
    else:
        print(f"✅ 所有类型都被使用过")

if __name__ == "__main__":
    print("🔍 调试轮询问题")
    
    # 测试不同的情况
    test_cases = [
        ("单类型账号", [1]),
        ("双类型账号", [1, 2]), 
        ("四类型账号", [1, 2, 3, 4]),
        ("五类型账号", [1, 2, 3, 4, 5])
    ]
    
    for case_name, types in test_cases:
        debug_polling_logic(case_name, types, rounds=15)
        print("\n" + "="*80 + "\n")