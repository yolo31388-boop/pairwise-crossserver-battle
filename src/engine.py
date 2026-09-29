"""跨服战场 - 带7个bug"""
from dataclasses import dataclass, field
import random

@dataclass class Player:
    pid: str
    server: str
    power: int
    score: int = 0

class CrossServerBattle:
    def __init__(self):
        self.queue = []
        self.matches = []
        self.afk_check = {}

    def match(self, players):
        # bug1: 不看服务器
        team_a = players[:len(players)//2]
        team_b = players[len(players)//2:]
        self.matches.append((team_a, team_b))
        return team_a, team_b

    def calc_score(self, player, won, kills, deaths):
        # bug2: 只看胜负
        return 100 if won else 0

    def normalize_stats(self, player):
        # bug3: 平衡不生效
        return player.power

    def award_rewards(self, match_id, player_id, participated=True):
        # bug5: 中途退出也给奖励
        return {"gold": 500}

    def is_afk(self, player_id, actions):
        # bug6: 只看移动
        movement = actions.get("movement", 0)
        return movement < 10

    def season_reset(self):
        # bug7: 不重置积分
        pass
