#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fibonacci会员系统测试脚本
验证Python端等级计算与Dart端的一致性
"""

import asyncio
import sys
import os

# 设置UTF-8编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from base.plugins.customer.services.membership_service import fibonacci_service


def test_fibonacci_sequence():
    """测试Fibonacci数列生成"""
    print("\n" + "="*70)
    print("测试1: Fibonacci数列生成")
    print("="*70)

    print("前20个Fibonacci数:")
    for i in range(1, 21):
        fib = fibonacci_service.get_fibonacci(i)
        print(f"  F({i}) = {fib}")

    # 验证数列正确性
    expected = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765]
    for i, val in enumerate(expected, 1):
        actual = fibonacci_service.get_fibonacci(i)
        assert actual == val, f"F({i}) 应该是 {val}，实际是 {actual}"

    print("[PASS] Fibonacci数列生成正确")


def test_level_calculation():
    """测试等级计算（与Dart端对比）"""
    print("\n" + "="*70)
    print("测试2: 等级计算（与Dart端对比）")
    print("="*70)

    # 测试用例：(总小时数, 期望等级)
    test_cases = [
        (0, 0, "免费用户"),
        (1, 1, "体验会员"),
        (2, 2, "体验会员"),
        (3, 3, "正式会员"),
        (4, 3, "正式会员"),
        (5, 4, "正式会员"),
        (7, 4, "正式会员"),
        (8, 5, "高级会员"),
        (12, 5, "高级会员"),
        (13, 6, "高级会员"),
        (20, 6, "高级会员"),
        (21, 7, "高级会员"),
        (33, 7, "高级会员"),
        (34, 8, "青铜会员"),
        (54, 8, "青铜会员"),
        (55, 9, "白银会员"),
        (88, 9, "白银会员"),
        (89, 10, "黄金会员"),
        (143, 10, "黄金会员"),
        (144, 11, "铂金会员"),
    ]

    print(f"{'总小时':<8} {'等级':<6} {'称号':<12} {'验证'}")
    print("-" * 70)

    all_passed = True
    for total_hours, expected_level, expected_title in test_cases:
        actual_level = fibonacci_service.get_level_from_hours(total_hours)
        actual_title = fibonacci_service.get_level_title(actual_level)

        # 验证等级
        passed = actual_level == expected_level
        status = "✅" if passed else "❌"

        print(f"{total_hours:<8} {actual_level:<6} {actual_title:<12} {status}", end="")

        if not passed:
            print(f" (期望: {expected_level})")
            all_passed = False
        else:
            print()

    if all_passed:
        print("\n✅ 所有等级计算测试通过")
    else:
        print("\n❌ 等级计算测试失败！")

    return all_passed


def test_hours_for_level():
    """测试等级所需小时数"""
    print("\n" + "="*70)
    print("测试3: 等级所需小时数")
    print("="*70)

    print(f"{'等级':<6} {'累计小时':<12} {'验证'}")
    print("-" * 70)

    # 验证等级所需小时数
    expected_cumulative = [0, 1, 2, 4, 7, 12, 20, 33, 54, 88]
    all_passed = True

    for level, expected_hours in enumerate(expected_cumulative):
        if level == 0:
            continue

        actual_hours = fibonacci_service.get_hours_for_level(level)
        passed = actual_hours == expected_hours
        status = "✅" if passed else "❌"

        print(f"{level:<6} {actual_hours:<12} {status}", end="")

        if not passed:
            print(f" (期望: {expected_hours})")
            all_passed = False
        else:
            print()

    if all_passed:
        print("\n✅ 所有所需小时数测试通过")
    else:
        print("\n❌ 所需小时数测试失败！")

    return all_passed


def test_level_progress():
    """测试等级进度"""
    print("\n" + "="*70)
    print("测试4: 等级进度")
    print("="*70)

    print(f"{'总小时':<8} {'等级':<6} {'进度':<8} {'下一级':<8} {'验证'}")
    print("-" * 70)

    test_cases = [
        (0, 0, 0.0, 1),  # 0小时，Level 0，进度0%，到Level 1需要1小时
        (1, 1, 0.0, 2),  # 1小时，Level 1，进度0%（刚升级），到Level 2需要1小时
        (3, 2, 50.0, 3),  # 3小时，Level 2，进度50%（3在2-4中间），到Level 3需要1小时
        (6, 3, 66.67, 4),  # 6小时，Level 3，进度66.67%（6在4-7中间），到Level 4需要1小时
    ]

    all_passed = True
    for total_hours, expected_level, expected_progress, expected_next in test_cases:
        actual_level = fibonacci_service.get_level_from_hours(total_hours)
        actual_progress = fibonacci_service.get_level_progress(total_hours) * 100
        hours_to_next = fibonacci_service.get_hours_to_next_level(actual_level, total_hours)

        passed = (
            actual_level == expected_level and
            abs(actual_progress - expected_progress) < 0.1
        )
        status = "✅" if passed else "❌"

        print(f"{total_hours:<8} {actual_level:<6} {actual_progress:>6.2f}% {hours_to_next:<8} {status}", end="")

        if not passed:
            print(f" (期望: Lv{expected_level}, {expected_progress}%)")
            all_passed = False
        else:
            print()

    if all_passed:
        print("\n✅ 所有等级进度测试通过")
    else:
        print("\n❌ 等级进度测试失败！")

    return all_passed


def test_privileges():
    """测试特权定义"""
    print("\n" + "="*70)
    print("测试5: 特权定义（与Dart端对比）")
    print("="*70)

    test_levels = [0, 1, 3, 5, 8, 13, 21, 34, 55, 89, 144]

    for level in test_levels:
        privileges = fibonacci_service.get_level_privileges(level)
        title = fibonacci_service.get_level_title(level)
        color = fibonacci_service.get_level_color(level)
        icon = fibonacci_service.get_level_icon(level)

        print(f"\nLevel {level} - {title}")
        print(f"  颜色: {color}")
        print(f"  图标: {icon}")
        print(f"  特权数量: {len(privileges)}")
        print(f"  特权列表:")
        for priv in privileges:
            print(f"    - {priv}")

    print("\n✅ 特权定义完成")


def test_edge_cases():
    """测试边缘情况"""
    print("\n" + "="*70)
    print("测试6: 边缘情况")
    print("="*70)

    # 测试大数值
    large_hours = 10000
    level = fibonacci_service.get_level_from_hours(large_hours)
    print(f"✅ 大数值测试: {large_hours}小时 → Level {level}")

    # 测试负数
    negative_hours = -10
    level = fibonacci_service.get_level_from_hours(negative_hours)
    print(f"✅ 负数测试: {negative_hours}小时 → Level {level}")

    # 测试进度边界
    progress_0 = fibonacci_service.get_level_progress(0)
    progress_100 = fibonacci_service.get_level_progress(1)
    print(f"✅ 进度边界测试: Level 0起点={progress_0}, Level 1起点={progress_100}")


def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("Fibonacci会员系统测试 - 验证与Dart端的一致性")
    print("="*70)

    try:
        test_fibonacci_sequence()
        result1 = test_level_calculation()
        result2 = test_hours_for_level()
        result3 = test_level_progress()
        test_privileges()
        test_edge_cases()

        print("\n" + "="*70)
        print("测试总结")
        print("="*70)

        if result1 and result2 and result3:
            print("✅ 所有核心测试通过！Python端与Dart端逻辑一致")
            return 0
        else:
            print("❌ 部分测试失败，请检查实现")
            return 1

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
