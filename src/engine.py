"""跨服战场 - 7个bug已修复"""
from dataclasses import dataclass, field
import time


@dataclass
class Player:
    pid: str
    server: str
    power: int
    score: int = 0


class CrossServerBattle:
    # bug3: 战场独立的属性归一化模板，进场后所有人按模板结算
    STAT_TEMPLATE = {"power": 100}
    # bug4: 转服后数据同步冷却期（秒），期间不能排跨服
    SYNC_COOLDOWN = 300
    # bug5: 中途退出惩罚
    QUIT_PENALTY_SCORE = 50
    BAN_DURATION = 600
    # bug6: 挂机检测阈值（移动 / 技能 / 输入频率）
    AFK_MOVEMENT_MIN = 10
    AFK_SKILL_MIN = 1
    AFK_INPUT_MIN = 5

    def __init__(self):
        self.queue = []
        self.matches = []
        self.afk_check = {}
        self.players = {}
        self.transfer_log = {}
        self.quitters = set()
        self.bans = {}
        self.season = 1

    def register_player(self, player):
        self.players[player.pid] = player

    # ---------- bug1: 匹配避免同服对阵 ----------
    def match(self, players, now=None):
        for p in players:
            self.register_player(p)
        eligible = [p for p in players if self.can_queue(p, now)]
        # 同服保护：按服务器分组，整组分配到同一队，绝不拆开对阵
        by_server = {}
        for p in eligible:
            by_server.setdefault(p.server, []).append(p)
        team_a, team_b = [], []
        power_a = power_b = 0
        for server in sorted(by_server):
            group = by_server[server]
            group_power = sum(p.power for p in group)
            if power_a <= power_b:
                team_a.extend(group)
                power_a += group_power
            else:
                team_b.extend(group)
                power_b += group_power
        self.matches.append((team_a, team_b))
        return team_a, team_b

    # ---------- bug2: 积分综合胜负 + 个人表现 ----------
    def calc_score(self, player, won, kills, deaths,
                   damage=0, healing=0, objective=0):
        base = 100 if won else 20
        performance = (
            kills * 10
            - deaths * 5
            + damage // 100
            + healing // 100
            + objective * 15
        )
        return max(0, base + performance)

    # ---------- bug3: 属性归一化模板 ----------
    def normalize_stats(self, player):
        return self.STAT_TEMPLATE["power"]

    # ---------- bug4: 转服数据同步冷却 ----------
    def transfer_server(self, player, new_server, now=None):
        now = time.time() if now is None else now
        player.server = new_server
        self.transfer_log[player.pid] = now

    def can_queue(self, player, now=None):
        last = self.transfer_log.get(player.pid)
        if last is None:
            return True
        now = time.time() if now is None else now
        return now - last >= self.SYNC_COOLDOWN

    def is_banned(self, player_id, now=None):
        until = self.bans.get(player_id)
        if until is None:
            return False
        now = time.time() if now is None else now
        return now < until

    # ---------- bug5: 中途退出惩罚 + 按有效参与发奖励 ----------
    def quit_match(self, match_id, player_id, now=None):
        now = time.time() if now is None else now
        self.quitters.add((match_id, player_id))
        self.bans[player_id] = now + self.BAN_DURATION
        player = self.players.get(player_id)
        if player is not None:
            player.score = max(0, player.score - self.QUIT_PENALTY_SCORE)

    def award_rewards(self, match_id, player_id, participated=True,
                      participation=1.0):
        quit_match = (match_id, player_id) in self.quitters
        if quit_match or not participated or participation <= 0:
            return {"gold": 0}
        participation = min(1.0, participation)
        return {"gold": int(500 * participation)}

    # ---------- bug6: 挂机检测综合移动/技能/输入频率 ----------
    def is_afk(self, player_id, actions):
        movement = actions.get("movement", 0)
        skills = actions.get("skills", actions.get("skill_casts", 0))
        inputs = actions.get("inputs", actions.get("input_count", 0))
        return (movement < self.AFK_MOVEMENT_MIN
                and skills < self.AFK_SKILL_MIN
                and inputs < self.AFK_INPUT_MIN)

    # ---------- bug7: 赛季结束积分清零 ----------
    def season_reset(self):
        for player in self.players.values():
            player.score = 0
        self.bans.clear()
        self.quitters.clear()
        self.season += 1
