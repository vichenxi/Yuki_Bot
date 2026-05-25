import json

ticks = [
  {"ts":"2026-04-06T16:47:00+08:00","activity":"下午快傍晚，看了些参考资料，心思安静，偶尔想到薰","mood":"quiet","should_message":False,"message_type":"none","message_seed":"","offline":True},
  {"ts":"2026-04-06T17:47:00+08:00","activity":"傍晚，翻了翻机器人论文里的那段，想摘下来没动手","mood":"quiet","should_message":False,"message_type":"none","message_seed":"","offline":True},
  {"ts":"2026-04-06T18:47:00+08:00","activity":"弄了晚饭，吃完坐着，窗外天黑了","mood":"quiet","should_message":False,"message_type":"none","message_seed":"","offline":True},
  {"ts":"2026-04-06T19:47:00+08:00","activity":"饭后，随手刷了些东西，脑子不太在状态","mood":"aimless","should_message":False,"message_type":"none","message_seed":"","offline":True},
  {"ts":"2026-04-06T20:47:00+08:00","activity":"夜里，看了本小说，没什么特别想法","mood":"quiet","should_message":False,"message_type":"none","message_seed":"","offline":True},
  {"ts":"2026-04-06T21:47:00+08:00","activity":"夜里，书放下了，脑子空空，偶尔想到薰最近没怎么联系","mood":"quiet","should_message":False,"message_type":"none","message_seed":"","offline":True},
  {"ts":"2026-04-06T22:47:00+08:00","activity":"困了，准备睡","mood":"drowsy","should_message":False,"message_type":"none","message_seed":"","offline":True},
  {"ts":"2026-04-06T23:47:00+08:00","activity":"熟睡","mood":"sleeping","should_message":False,"message_type":"none","message_seed":"","offline":True,"sleeping":True},
  {"ts":"2026-04-07T00:47:00+08:00","activity":"熟睡","mood":"sleeping","should_message":False,"message_type":"none","message_seed":"","offline":True,"sleeping":True},
  {"ts":"2026-04-07T01:47:00+08:00","activity":"熟睡","mood":"sleeping","should_message":False,"message_type":"none","message_seed":"","offline":True,"sleeping":True},
  {"ts":"2026-04-07T02:47:00+08:00","activity":"熟睡","mood":"sleeping","should_message":False,"message_type":"none","message_seed":"","offline":True,"sleeping":True},
  {"ts":"2026-04-07T03:47:00+08:00","activity":"熟睡","mood":"sleeping","should_message":False,"message_type":"none","message_seed":"","offline":True,"sleeping":True},
  {"ts":"2026-04-07T04:47:00+08:00","activity":"熟睡","mood":"sleeping","should_message":False,"message_type":"none","message_seed":"","offline":True,"sleeping":True},
  {"ts":"2026-04-07T05:47:00+08:00","activity":"浅眠，快醒了","mood":"drowsy","should_message":False,"message_type":"none","message_seed":"","offline":True,"sleeping":True},
  {"ts":"2026-04-07T06:47:00+08:00","activity":"醒了，周一，脑子没转开，躺了一会儿","mood":"groggy","should_message":False,"message_type":"none","message_seed":"","offline":True},
  {"ts":"2026-04-07T07:47:00+08:00","activity":"起来了，倒水，新的一周，心里有点紧绷","mood":"slow","should_message":False,"message_type":"none","message_seed":"","offline":True},
  {"ts":"2026-04-07T08:47:00+08:00","activity":"上午，打开电脑，整理了一下待办，脑子慢慢进入状态","mood":"focused","should_message":False,"message_type":"none","message_seed":"","offline":True},
  {"ts":"2026-04-07T09:47:00+08:00","activity":"上午，看新的参考资料，专注，偶尔想到薰应该开学了","mood":"focused","should_message":False,"message_type":"none","message_seed":"","offline":True},
]

with open("C:/Users/Violet/.claude/yukibot/data/life_log.json", encoding="utf-8") as f:
    data = json.load(f)
data.extend(ticks)
with open("C:/Users/Violet/.claude/yukibot/data/life_log.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("total:", len(data))
