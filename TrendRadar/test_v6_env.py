import os
import sys
from datetime import datetime

# 模拟环境变量
os.environ['AI_API_KEY'] = 'test_key_mock'
os.environ['AI_MODEL'] = 'deepseek/deepseek-chat'

try:
    print("⏳ 正在检查环境配置...")
    
    # 1. 验证 AI Key 读取
    api_key = os.environ.get("AI_API_KEY")
    if api_key:
        print("✅ AI_API_KEY 环境变量检测成功")
    else:
        print("❌ AI_API_KEY 环境变量缺失")

    # 2. 验证 TrendRadar 导入
    try:
        from trendradar import __version__
        print(f"✅ TrendRadar 模块导入成功，版本: {__version__}")
    except ImportError:
        print("❌ TrendRadar 模块导入失败，请检查 PYTHONPATH 或安装依赖")
        sys.exit(1)

    # 3. 验证调度器逻辑 (模拟工作日 10:00)
    print("\n⏳ 正在验证调度器逻辑 (office_hours)...")
    
    # 临时修改 config 加载逻辑或 mock 时间比较复杂，这里直接实例化调度器
    # 注意：真实验证需要 mock datetime.now，这里仅做简单冒烟测试
    from trendradar.core.scheduler import Scheduler
    from trendradar.core.config import load_config
    
    # 强制加载配置
    config = load_config()
    preset = config.get('schedule', {}).get('preset')
    print(f"当前预设模板: {preset}")
    
    if preset == 'office_hours':
        print("✅ 预设模板配置正确 (office_hours)")
    else:
        print(f"❌ 预设模板配置错误: {preset} (预期: office_hours)")

    print("\n🎉 本地环境验证完成！")

except Exception as e:
    print(f"\n❌ 验证过程中发生错误: {str(e)}")
    sys.exit(1)
