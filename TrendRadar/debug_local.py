import os
import sys
import subprocess
from pathlib import Path

def load_env_file(env_path):
    """简单的 .env 文件加载器"""
    if not env_path.exists():
        print(f"⚠️ 未找到配置文件: {env_path}")
        print(f"请复制 .env.example 为 {env_path.name} 并填入你的配置")
        return False
        
    print(f"✅ 正在加载配置: {env_path}")
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 处理 key=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # 去除引号
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                    
                if key:
                    os.environ[key] = value
                    # 隐藏敏感信息显示
                    display_value = value[:6] + "******" if "KEY" in key or "TOKEN" in key else value
                    print(f"  -> 设置环境变量: {key} = {display_value}")
    return True

def main():
    root_dir = Path(__file__).parent
    env_file = root_dir / ".env.local"
    
    print("=" * 60)
    print("TrendRadar 本地调试启动器")
    print("=" * 60)
    
    # 1. 加载环境变量
    if not load_env_file(env_file):
        # 如果没有 .env.local，询问是否创建模板
        create = input("\n是否创建 .env.local 模板文件? (y/n): ").lower()
        if create == 'y':
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write("# 本地调试配置文件 (请勿提交到 Git)\n")
                f.write("# 在这里填入你的真实 Key 进行测试\n\n")
                f.write("# AI API Key\n")
                f.write("AI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx\n\n")
                f.write("# 自定义 Webhook (用于测试推送)\n")
                f.write("# FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/...\n")
                f.write("# GENERIC_WEBHOOK_URL=http://your-custom-webhook-url\n")
            print(f"✅ 已创建 {env_file}，请编辑后重新运行此脚本")
        return

    # 2. 确认执行模式
    print("\n调试选项:")
    print("1. 正常运行 (python -m trendradar)")
    print("2. 查看调度状态 (python -m trendradar --show-schedule)")
    
    choice = input("\n请选择 (默认 1): ").strip()
    
    cmd = [sys.executable, "-m", "trendradar"]
    if choice == "2":
        cmd.append("--show-schedule")
    
    print(f"\n🚀 开始执行命令: {' '.join(cmd)}")
    print("-" * 60)
    
    # 3. 执行命令
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 执行出错: {e}")
    except KeyboardInterrupt:
        print("\n🛑 用户终止")

if __name__ == "__main__":
    main()
