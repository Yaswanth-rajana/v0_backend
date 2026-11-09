import unittest
import json
import os
os.environ['TESTING'] = 'True'

from app import app
from models import db, SuperTournament, Season, Tournament, Match, Team, Player, Score
from routes.score.score_core import update_successor_match

class TestWinnerProgression(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Seed hierarchy
        st = SuperTournament(id=1, name="ST")
        se = Season(id=1, super_tournament_id=1, name="S1")
        tr = Tournament(id=1, season_id=1, tournament_name="T1", type="regular")
        db.session.add_all([st, se, tr])

        # Seed 4 teams
        for t_id, name in [('TA', 'Team A'), ('TB', 'Team B'), ('TC', 'Team C'), ('TD', 'Team D')]:
            db.session.add(Team(team_id=t_id, name=name, tournament_id=1))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_team_a_wins_by_walkover_advances_to_successor(self):
        """Team A wins by walkover -> Team A appears in successor as team1_id"""
        # Match 1: TA vs TB, successor = 3
        # Match 3: successor match (pred1=1, pred2=2)
        m1 = Match(id=1, match_name="Semi 1", team1_id="TA", team2_id="TB", round_id="1", pool="A", tournament_id=1, successor=3, status="pending")
        m3 = Match(id=3, match_name="Final", team1_id=None, team2_id=None, round_id="2", pool="A", tournament_id=1, predecessor_1=1, predecessor_2=2, status="pending")
        db.session.add_all([m1, m3])
        db.session.commit()

        # Declare walkover for TA
        res = self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "TA"
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)

        # Verify successor
        m3_updated = Match.query.get(3)
        self.assertEqual(m3_updated.team1_id, "TA")
        self.assertIsNone(m3_updated.team2_id)

    def test_team_b_wins_by_walkover_advances_to_successor(self):
        """Team B wins by walkover -> Team B appears in successor as team1_id"""
        m1 = Match(id=1, match_name="Semi 1", team1_id="TA", team2_id="TB", round_id="1", pool="A", tournament_id=1, successor=3, status="pending")
        m3 = Match(id=3, match_name="Final", team1_id=None, team2_id=None, round_id="2", pool="A", tournament_id=1, predecessor_1=1, predecessor_2=2, status="pending")
        db.session.add_all([m1, m3])
        db.session.commit()

        # Declare walkover for TB
        res = self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "TB"
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)

        # Verify successor
        m3_updated = Match.query.get(3)
        self.assertEqual(m3_updated.team1_id, "TB")
        self.assertIsNone(m3_updated.team2_id)

    def test_team_c_wins_match2_by_walkover_advances_as_team2(self):
        """Team C wins Match 2 (predecessor 2) by walkover -> Team C appears in successor as team2_id"""
        m2 = Match(id=2, match_name="Semi 2", team1_id="TC", team2_id="TD", round_id="1", pool="A", tournament_id=1, successor=3, status="pending")
        m3 = Match(id=3, match_name="Final", team1_id="TA", team2_id=None, round_id="2", pool="A", tournament_id=1, predecessor_1=1, predecessor_2=2, status="pending")
        db.session.add_all([m2, m3])
        db.session.commit()

        # Declare walkover for TC
        res = self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 2,
            "tournament_id": 1,
            "winning_team_id": "TC"
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)

        m3_updated = Match.query.get(3)
        self.assertEqual(m3_updated.team1_id, "TA")
        self.assertEqual(m3_updated.team2_id, "TC")

    def test_team_d_wins_match2_by_walkover_advances_as_team2(self):
        """Team D wins Match 2 by walkover -> Team D appears in successor as team2_id"""
        m2 = Match(id=2, match_name="Semi 2", team1_id="TC", team2_id="TD", round_id="1", pool="A", tournament_id=1, successor=3, status="pending")
        m3 = Match(id=3, match_name="Final", team1_id="TB", team2_id=None, round_id="2", pool="A", tournament_id=1, predecessor_1=1, predecessor_2=2, status="pending")
        db.session.add_all([m2, m3])
        db.session.commit()

        # Declare walkover for TD
        res = self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 2,
            "tournament_id": 1,
            "winning_team_id": "TD"
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)

        m3_updated = Match.query.get(3)
        self.assertEqual(m3_updated.team1_id, "TB")
        self.assertEqual(m3_updated.team2_id, "TD")

    def test_regular_winner_progression_intact(self):
        """Verify normal match progression is completely intact"""
        m1 = Match(id=1, match_name="Semi 1", team1_id="TA", team2_id="TB", round_id="1", pool="A", tournament_id=1, successor=3, status="pending")
        m3 = Match(id=3, match_name="Final", team1_id=None, team2_id=None, round_id="2", pool="A", tournament_id=1, predecessor_1=1, predecessor_2=2, status="pending")
        db.session.add_all([m1, m3])
        db.session.commit()

        # Finalize regular match with score
        res = self.client.post('/update-score', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "score": "15-10",
            "final": True
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)

        m3_updated = Match.query.get(3)
        self.assertEqual(m3_updated.team1_id, "TA")

if __name__ == '__main__':
    unittest.main()
