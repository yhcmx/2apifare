"""
测试 Antigravity 配置读取功能

测试场景：
1. 默认值测试（无环境变量）
2. 环境变量测试（true/false）
3. 各种布尔值格式测试
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_antigravity_skip_project_verification


async def test_default_value():
    """测试默认值（应该是 False）"""
    print("\n" + "="*60)
    print("测试 1: 默认值（无环境变量）")
    print("="*60)

    # 确保环境变量未设置
    os.environ.pop('ANTIGRAVITY_SKIP_PROJECT_VERIFICATION', None)

    result = await get_antigravity_skip_project_verification()
    expected = False

    print(f"预期值: {expected}")
    print(f"实际值: {result}")
    print(f"状态: {'[PASS] 通过' if result == expected else '[FAIL] 失败'}")

    assert result == expected, f"默认值应该是 {expected}"


async def test_env_true_values():
    """测试环境变量设为 true 的各种格式"""
    print("\n" + "="*60)
    print("测试 2: 环境变量设为 true（多种格式）")
    print("="*60)

    true_values = ["true", "True", "TRUE", "1", "yes", "Yes", "YES", "on", "On", "ON"]

    for value in true_values:
        os.environ['ANTIGRAVITY_SKIP_PROJECT_VERIFICATION'] = value
        result = await get_antigravity_skip_project_verification()

        print(f"  '{value}' -> {result} {'[OK]' if result else '[FAIL]'}")
        assert result == True, f"'{value}' 应该被识别为 True"

    print(f"\n状态: [PASS] 所有 true 格式测试通过")


async def test_env_false_values():
    """测试环境变量设为 false 的各种格式"""
    print("\n" + "="*60)
    print("测试 3: 环境变量设为 false（多种格式）")
    print("="*60)

    false_values = ["false", "False", "FALSE", "0", "no", "No", "NO", "off", "Off", "OFF", ""]

    for value in false_values:
        os.environ['ANTIGRAVITY_SKIP_PROJECT_VERIFICATION'] = value
        result = await get_antigravity_skip_project_verification()

        print(f"  '{value}' -> {result} {'[OK]' if not result else '[FAIL]'}")
        assert result == False, f"'{value}' 应该被识别为 False"

    print(f"\n状态: [PASS] 所有 false 格式测试通过")


async def test_pro_account_scenario():
    """测试 Pro 账号场景"""
    print("\n" + "="*60)
    print("测试 4: Pro 账号场景（跳过验证）")
    print("="*60)

    os.environ['ANTIGRAVITY_SKIP_PROJECT_VERIFICATION'] = 'true'
    result = await get_antigravity_skip_project_verification()

    print(f"配置: ANTIGRAVITY_SKIP_PROJECT_VERIFICATION=true")
    print(f"结果: {result}")
    print(f"含义: {'Pro 账号模式 - 跳过验证，使用随机 projectId' if result else '免费账号模式 - 需要 API 验证'}")
    print(f"状态: [PASS] Pro 账号配置正确")

    assert result == True


async def test_free_account_scenario():
    """测试免费账号场景"""
    print("\n" + "="*60)
    print("测试 5: 免费账号场景（需要验证）")
    print("="*60)

    os.environ['ANTIGRAVITY_SKIP_PROJECT_VERIFICATION'] = 'false'
    result = await get_antigravity_skip_project_verification()

    print(f"配置: ANTIGRAVITY_SKIP_PROJECT_VERIFICATION=false")
    print(f"结果: {result}")
    print(f"含义: {'Pro 账号模式 - 跳过验证，使用随机 projectId' if result else '免费账号模式 - 需要 API 验证'}")
    print(f"状态: [PASS] 免费账号配置正确")

    assert result == False


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Antigravity 配置读取功能测试")
    print("="*60)

    try:
        await test_default_value()
        await test_env_true_values()
        await test_env_false_values()
        await test_pro_account_scenario()
        await test_free_account_scenario()

        print("\n" + "="*60)
        print("所有测试通过！")
        print("="*60)
        print("\n配置功能正常，可以继续实现下一步功能。\n")

    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 未预期的错误: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
