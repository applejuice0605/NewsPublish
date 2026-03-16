import sys
import json
import os
from ruamel.yaml import YAML

def sync_config(json_path, yaml_path):
    # 检查文件是否存在
    if not os.path.exists(json_path):
        print(f"❌ JSON file not found: {json_path}")
        return
    if not os.path.exists(yaml_path):
        print(f"❌ YAML file not found: {yaml_path}")
        return

    yaml = YAML()
    yaml.preserve_quotes = True
    
    try:
        # 1. 读取新配置 (JSON)
        with open(json_path, 'r', encoding='utf-8') as f:
            new_config = json.load(f)
            
        # 2. 读取旧配置 (YAML - 保留注释模式)
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f)
            
        # 3. 递归更新字段 (示例：仅更新 schedule 和 platforms)
        # 注意：ruamel.yaml 对象操作类似字典，直接赋值即可保留原有注释
        if 'schedule' in new_config:
            if 'schedule' not in config:
                config['schedule'] = {}
            # 递归更新 schedule 下的字段，而不是直接覆盖，以保留可能的注释
            for key, value in new_config['schedule'].items():
                config['schedule'][key] = value
            
        if 'platforms' in new_config:
             config['platforms'] = new_config['platforms']
             
        # 更新其他可能的配置项
        if 'rss' in new_config:
            config['rss'] = new_config['rss']
            
        if 'report' in new_config:
            # 递归更新 report
            if 'report' not in config:
                config['report'] = {}
            for key, value in new_config['report'].items():
                config['report'][key] = value
                
        if 'display' in new_config:
            config['display'] = new_config['display']
            
        if 'notification' in new_config:
            # notification 通常包含敏感信息，且结构复杂，建议只更新非敏感部分或谨慎覆盖
            # 这里演示更新 enabled 状态
             if 'enabled' in new_config['notification']:
                 config['notification']['enabled'] = new_config['notification']['enabled']
    
        # 4. 写回文件
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
        print(f"✅ Config synced to {yaml_path}")
        
    except Exception as e:
        print(f"❌ Error syncing config: {str(e)}")

if __name__ == "__main__":
    # 使用方法: python sync_config.py exported.json config/config.yaml
    if len(sys.argv) < 3:
        print("Usage: python sync_config.py <json_path> <yaml_path>")
    else:
        sync_config(sys.argv[1], sys.argv[2])
