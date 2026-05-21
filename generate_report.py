#!/usr/bin/env python3
"""
睡神 Agent 报告生成器
由 Hermes cron job 在凌晨调用：读取 sleep-log.json → 调用 DeepSeek API → 生成 morning-report.json
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Paths
DATA_DIR = Path('/root/.hermes/projects/sleep-agent/data')
SLEEP_LOG = DATA_DIR / 'sleep-log.json'
MORNING_REPORT = DATA_DIR / 'morning-report.json'

# DeepSeek API config
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')
DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
DEEPSEEK_MODEL = 'deepseek-chat'

if not DEEPSEEK_API_KEY:
    print('❌ No API key found. Set DEEPSEEK_API_KEY or OPENAI_API_KEY.')
    sys.exit(1)


def call_deepseek(prompt: str, system_prompt: str) -> str:
    """Call DeepSeek Chat API and return the response text."""
    import urllib.request
    import urllib.error

    url = f'{DEEPSEEK_BASE_URL}/chat/completions'
    payload = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 1500,
        'stream': False
    }).encode('utf-8')

    req = urllib.request.Request(url, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {DEEPSEEK_API_KEY}')

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        raise RuntimeError(f'DeepSeek API error {e.code}: {error_body}')


def generate_report():
    """Main: read sleep log, call DeepSeek, save report."""
    if not SLEEP_LOG.exists():
        print(f'⚠️  No sleep log found at {SLEEP_LOG}. Creating default report.')
        sleep_data = {
            'caffeine': 'none',
            'exercise': 'none',
            'stress': 5,
            'bedtime': '23:00',
            'notes': '未记录'
        }
    else:
        sleep_data = json.loads(SLEEP_LOG.read_text(encoding='utf-8'))

    # Map values to Chinese descriptions
    caffeine_map = {
        'none': '今天没有摄入咖啡因',
        'morning': '上午喝了1杯咖啡/茶',
        'afternoon': '下午喝了1杯咖啡/茶',
        'heavy': '全天摄入2杯以上咖啡因饮品'
    }
    exercise_map = {
        'none': '今天没有运动',
        'light': '轻度运动，不到30分钟',
        'moderate': '中度运动，30-60分钟',
        'intense': '高强度运动，超过60分钟'
    }

    caffeine_desc = caffeine_map.get(sleep_data.get('caffeine', 'none'), '未知')
    exercise_desc = exercise_map.get(sleep_data.get('exercise', 'none'), '未知')
    stress = sleep_data.get('stress', 5)
    bedtime = sleep_data.get('bedtime', '23:00')
    notes = sleep_data.get('notes', '').strip()

    # Build system prompt
    system_prompt = """你是一位温柔、专业的中文睡眠健康顾问，名字叫「睡神 Hypnos」。
你的风格：
- 温暖治愈，像宫崎骏电影里的温柔角色
- 用优美的中文，加入适当的诗意
- 科学性 + 人文关怀并重
- 给出具体可行的建议，不说空话
- 报告格式用 Markdown（### 标题, **加粗**, - 列表项）

每份报告包含：
1. 睡眠质量预测（基于输入数据推断）
2. 今日健康洞察（压力/运动/咖啡因如何影响睡眠）
3. 明日建议（饮食、作息、心态三方面）
4. 一句温暖的睡前/晨间寄语"""

    user_prompt = f"""请根据以下睡前数据，生成一份温暖的明日晨间健康简报：

📊 今日数据：
- 咖啡因摄入：{caffeine_desc}
- 运动情况：{exercise_desc}
- 压力水平：{stress}/10 {'（偏高，需要放松）' if stress >= 7 else '（适中）' if stress >= 4 else '（较低，状态不错）'}
- 预计就寝：{bedtime}
{f'- 心情备注：{notes}' if notes else ''}

请用温柔、专业的语气，生成一份让人读起来感到被关心的健康简报。"""

    print(f'🤖 Calling DeepSeek API ({DEEPSEEK_MODEL})...')
    try:
        content = call_deepseek(user_prompt, system_prompt)
    except Exception as e:
        print(f'❌ API call failed: {e}')
        content = f"""### 早安 ☀️

睡神暂时无法连接云端分析服务。

不过别担心——昨晚的数据已经被记录下来了：
- 咖啡因：{caffeine_desc}
- 运动：{exercise_desc}
- 压力水平：{stress}/10

**今日小建议：** 保持规律作息，记得多喝水，给自己一个温柔的早晨。

*睡神会在下次成功连接后为你补上完整分析 ✨*"""

    # Build report
    today = datetime.now().strftime('%Y-%m-%d')
    report = {
        'date': today,
        'generated_at': datetime.now().isoformat(),
        'input_summary': {
            'caffeine': sleep_data.get('caffeine', 'none'),
            'exercise': sleep_data.get('exercise', 'none'),
            'stress': stress,
            'bedtime': bedtime,
        },
        'content': content
    }

    MORNING_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'✅ Report saved to {MORNING_REPORT}')
    print(f'📋 Preview: {content[:200]}...')
    return report


if __name__ == '__main__':
    generate_report()
