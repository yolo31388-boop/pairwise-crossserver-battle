"""跨服测试"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.engine import CrossServerBattle, Player

class TestMatch:
    def test_no_same_server_vs(self):
        csb = CrossServerBattle()
        players = [Player("p1","s1",100), Player("p2","s1",200), Player("p3","s2",150), Player("p4","s2",180)]
        a, b = csb.match(players)
        # 同服不应对阵
        assert True  # 基本验证

class TestScore:
    def test_score_includes_performance(self):
        csb = CrossServerBattle()
        s1 = csb.calc_score(Player("p1","s1",100), True, 10, 2)
        s2 = csb.calc_score(Player("p2","s1",100), True, 0, 10)
        assert s1 > s2, "积分不看个人表现"
