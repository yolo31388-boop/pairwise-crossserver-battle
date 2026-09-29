"""跨服战场 - 7个bug已修复"""
from dataclasses import dataclass, field
import time

@dataclass
class Player:
    pid: str
    server: str
    power: int
    score: int = 0

# 战场属性归一化模板（bug3）：进场后战力被压缩到模板区间内
NORMALIZE_TEMPLATE = {"base": 100, "scale": 0.2, "cap": 300}

# 转服数据同步冷却期（秒）（bug4）：冷却期内不能排跨服
TRANSFER_SYNC_COOLDOWN = 300

# 中途退出惩罚（bug5）
QUIT_PENALTY_SCORE = 50
QUIT_BAN_SECONDS = 600

# 挂机检测权重与阈值（bug6）：综合移动、技能、输入频率
AFK_WEIGHTS = {"movement": 1, "skills": 5, "inputs": 2}
AFK_THRESHOLD = 10

# 赛季衰减比例（bug7）：新赛季积分按比例衰减后重新定位
SEASON_DECAY_RATIO = 0.0

class CrossServerBattle:
    def __init__(self):
        self.queue = []
        self.matches = []
        self.afk_check = {}
        self.players = {}
        self.transfer_log = {}
        self.ban_log = {}

    # bug4: 转服后记录时间，冷却期内禁止排跨服
    def record_transfer(self, player, now=None):
        self.transfer_log[player.pid] = time.time() if now is None else now

    def in_transfer_cooldown(self, player, now=None):
        now = time.time() if now is None else now
        ts = self.transfer_log.get(player.pid)
        return ts is not None and now - ts < TRANSFER_SYNC_COOLDOWN

    def can_queue(self, player, now=None):
        now = time.time() if now is None else now
        banned_until = self.ban_log.get(player.pid, 0)
        return not self.in_transfer_cooldown(player, now) and now >= banned_until

    # bug1: 按服务器分组匹配，同服玩家分到同队，避免内战
    def match(self, players, now=None):
        now = time.time() if now is None else now
        eligible = [p for p in players if self.can_queue(p, now)]
        for p in eligible:
            self.players[p.pid] = p
        groups = {}
        for p in eligible:
            groups.setdefault(p.server, []).append(p)
        team_a, team_b = [], []
        power_a = power_b = 0
        for server in sorted(groups, key=lambda s: -sum(p.power for p in groups[s])):
            grp = groups[server]
            grp_power = sum(p.power for p in grp)
            if power_a <= power_b:
                team_a.extend(grp); power_a += grp_power
            else:
                team_b.extend(grp); power_b += grp_power
        self.matches.append((team_a, team_b))
        return team_a, team_b

    # bug2: 积分 = 胜负基础分 + 个人表现（击杀/死亡/输出/治疗/占点）
    def calc_score(self, player, won, kills, deaths,
                   damage=0, healing=0, objective=0):
        base = 100 if won else 20
        performance = (kills * 10 - deaths * 5
                       + damage // 1000 + healing // 1000 + objective * 15)
        return max(0, base + performance)

    # bug3: 使用归一化模板压缩战力，高战力不再碾压
    def normalize_stats(self, player):
        t = NORMALIZE_TEMPLATE
        normalized = t["base"] + int(player.power * t["scale"])
        return min(normalized, t["cap"])

    # bug5: 中途退出扣分+禁赛；奖励按有效参与时长比例发放
    def award_rewards(self, match_id, player_id, participated=True,
                      participation=1.0, quit_midway=False, now=None):
        player = self.players.get(player_id)
        if quit_midway or not participated:
            if player is not None:
                player.score = max(0, player.score - QUIT_PENALTY_SCORE)
            self.ban_log[player_id] = (time.time() if now is None else now) + QUIT_BAN_SECONDS
            return {"gold": 0, "penalty": QUIT_PENALTY_SCORE, "banned": True}
        ratio = max(0.0, min(1.0, participation))
        return {"gold": int(500 * ratio)}

    # bug6: 综合移动、技能释放、输入频率多维度判定挂机
    def is_afk(self, player_id, actions):
        activity = (actions.get("movement", 0) * AFK_WEIGHTS["movement"]
                    + actions.get("skills", 0) * AFK_WEIGHTS["skills"]
                    + actions.get("inputs", 0) * AFK_WEIGHTS["inputs"])
        afk = activity < AFK_THRESHOLD
        self.afk_check[player_id] = afk
        return afk

    # bug7: 赛季结束积分清零/衰减，新赛季重新定位
    def season_reset(self, decay_ratio=SEASON_DECAY_RATIO):
        for player in self.players.values():
            player.score = int(player.score * decay_ratio)
        self.matches = []
        self.afk_check = {}
