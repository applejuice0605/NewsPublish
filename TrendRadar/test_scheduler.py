import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from datetime import datetime
import yaml

# 添加项目根目录到 path 以便导入模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 假设项目结构允许导入
from trendradar.core.scheduler import Scheduler 

class TestScheduler(unittest.TestCase):
    
    def setUp(self):
        # 准备一个模拟的 timeline_data，模拟从 timeline.yaml 加载的数据
        self.mock_timeline_data = {
            "presets": {
                "office_hours": {
                    "name": "办公时间",
                    "default": {
                        "collect": True,
                        "analyze": False,
                        "ai_mode": "current",
                        "push": False,
                        "report_mode": "current",
                        "once": {"analyze": True, "push": True}
                    },
                    "periods": {
                        "morning_briefing": {
                            "name": "到岗速览",
                            "start": "09:00",
                            "end": "11:00",
                            "analyze": True,
                            "ai_mode": "current",
                            "push": True,
                            "report_mode": "current"
                        },
                        "noon_update": {
                            "name": "午间热点",
                            "start": "13:00",
                            "end": "15:00",
                            "push": True,
                            "report_mode": "current"
                        },
                        "closing_summary": {
                            "name": "收工汇总",
                            "start": "17:00",
                            "end": "19:00",
                            "analyze": True,
                            "ai_mode": "daily",
                            "push": True,
                            "report_mode": "daily"
                        },
                        "weekend_free": {
                            "name": "周末自由",
                            "start": "08:00",
                            "end": "23:00",
                            "ai_mode": "current",
                            "push": True,
                            "report_mode": "incremental",
                            "once": {"analyze": False, "push": False}
                        }
                    },
                    "day_plans": {
                        "workday": {"periods": ["morning_briefing", "noon_update", "closing_summary"]},
                        "weekend": {"periods": ["weekend_free"]}
                    },
                    "week_map": {
                        1: "workday", 2: "workday", 3: "workday", 4: "workday", 5: "workday",
                        6: "weekend", 7: "weekend"
                    }
                }
            }
        }
    
    def test_office_hours_logic(self):
        # 1. 模拟配置为 office_hours
        schedule_config = {'enabled': True, 'preset': 'office_hours'}
        
        # 2. Mock storage_backend (不需要真实存储)
        mock_storage = MagicMock()
        mock_storage.has_period_executed.return_value = False # 假设今天还没执行过
        
        # 3. 定义不同时间点的测试用例
        test_cases = [
            # (时间描述, 模拟时间(周一), 预期 push, 预期 period_name)
            ("周一 10:30 (到岗速览)", datetime(2023, 10, 23, 10, 30), True, "到岗速览"),
            ("周一 12:00 (非推送时间)", datetime(2023, 10, 23, 12, 00), False, None),
            ("周一 14:00 (午间热点)", datetime(2023, 10, 23, 14, 00), True, "午间热点"),
            ("周一 18:00 (收工汇总)", datetime(2023, 10, 23, 18, 00), True, "收工汇总"),
            ("周六 10:00 (周末自由)", datetime(2023, 10, 28, 10, 00), True, "周末自由"),
        ]
        
        for desc, mock_time, expected_push, expected_period_name in test_cases:
            with self.subTest(msg=desc):
                # 构造调度器，注入模拟的 get_time 函数
                scheduler = Scheduler(
                    schedule_config=schedule_config,
                    timeline_data=self.mock_timeline_data,
                    storage_backend=mock_storage,
                    get_time_func=lambda: mock_time
                )
                
                # 执行解析
                action = scheduler.resolve()
                
                # 验证结果
                self.assertEqual(action.push, expected_push, f"{desc} 推送状态不符合预期")
                if expected_period_name:
                    self.assertEqual(action.period_name, expected_period_name, f"{desc} 时间段名称不符合预期")
                else:
                    self.assertIsNone(action.period_name, f"{desc} 应该不在任何时间段内")

if __name__ == '__main__':
    unittest.main()
