import unittest
import os
import json

os.environ['TESTING'] = 'True'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

from app import app
from models import db, Tournament, Season, SuperTournament, Team, Match, Score, Player, Round
from sqlalchemy import text

class WalkoverTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
            
            # Setup seed data
            st = SuperTournament(id=1, name="Test Super Tournament")
            db.session.add(st)
            
            season = Season(id=1, name="Season 1", super_tournament_id=1)
            db.session.add(season)
            
            tournament = Tournament(id=1, tournament_name="Test Tournament", type="regular", season_id=1)
            db.session.add(tournament)
            
            team1 = Team(team_id="T1", name="Alpha Warriors", tournament_id=1)
            team2 = Team(team_id="T2", name="Beta Titans", tournament_id=1)
            team3 = Team(team_id="T3", name="Gamma Strikers", tournament_id=1)
            db.session.add_all([team1, team2, team3])
            
            # Match 1: Round 1 match (Predecessor)
            # Match 2: Next round match (Successor)
            m2 = Match(
                id=2,
                match_name="Semi-Final 1",
                round_id="2",
                pool="knockout",
                tournament_id=1,
                status="pending"
            )
            db.session.add(m2)
            db.session.flush()
            
            m1 = Match(
                id=1,
                match_name="Quarter-Final 1",
                team1_id="T1",
                team2_id="T2",
                round_id="1",
                pool="knockout",
                tournament_id=1,
                status="pending",
                successor=2
            )
            db.session.add(m1)
            m2.predecessor_1 = 1
            
            s1 = Score(match_id=1, team_id="T1", score=0, tournament_id=1)
            s2 = Score(match_id=1, team_id="T2", score=0, tournament_id=1)
            db.session.add_all([s1, s2])
            
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_normal_score_update(self):
        """Test regular match score updating preserves existing behavior"""
        payload = {
            "match_id": 1,
            "tournament_id": 1,
            "score": "11-9",
            "final": False
        }
        res = self.client.post('/update-score', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['team1_score'], 11)
        self.assertEqual(data['team2_score'], 9)
        self.assertFalse(data['is_final'])
        self.assertFalse(data['is_walkover'])
        self.assertEqual(data['result_type'], 'regular')

    def test_normal_score_finalize(self):
        """Test regular match finalization determines winner by score"""
        payload = {
            "match_id": 1,
            "tournament_id": 1,
            "score": "15-11",
            "final": True
        }
        res = self.client.post('/update-score', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['is_final'])
        self.assertEqual(data['winner_team_id'], "T1")
        self.assertFalse(data['is_walkover'])
        self.assertEqual(data['result_type'], 'regular')

    def test_walkover_team1_wins(self):
        """Test declaring walkover for Team 1"""
        payload = {
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T1"
        }
        res = self.client.post('/declare-walkover', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['is_walkover'])
        self.assertEqual(data['result_type'], 'walkover')
        self.assertEqual(data['winner_team_id'], "T1")
        self.assertEqual(data['losing_team_id'], "T2")
        self.assertEqual(data['status'], 'completed')
        self.assertTrue(data['is_final'])

    def test_walkover_team2_wins(self):
        """Test declaring walkover for Team 2"""
        payload = {
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T2"
        }
        res = self.client.post('/declare-walkover', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['is_walkover'])
        self.assertEqual(data['winner_team_id'], "T2")
        self.assertEqual(data['losing_team_id'], "T1")

    def test_walkover_invalid_winning_team(self):
        """Test declaring walkover with a team not participating in the match"""
        payload = {
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T3"  # T3 is not in match 1 (T1 vs T2)
        }
        res = self.client.post('/declare-walkover', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("not a participant", data['error'])

    def test_walkover_match_not_found(self):
        """Test declaring walkover for non-existent match"""
        payload = {
            "match_id": 9999,
            "tournament_id": 1,
            "winning_team_id": "T1"
        }
        res = self.client.post('/declare-walkover', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 404)

    def test_walkover_already_finalized_prevents_duplicate(self):
        """3. Walkover duplicate submission: duplicate submission on finalized match is rejected"""
        # First finalize
        self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T1"
        }), content_type='application/json')
        
        # Second attempt without override
        res = self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T2"
        }), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("already been finalized", data['error'])

    def test_walkover_overwrite_with_override_false(self):
        """4. Attempted Walkover overwrite with override=false is rejected"""
        # Finalize match
        self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T1"
        }), content_type='application/json')
        
        # Overwrite attempt with override=False
        res = self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T2",
            "override": False
        }), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("already been finalized", data['error'])

    def test_walkover_overwrite_with_override_true(self):
        """5. Attempted Walkover overwrite with override=true is strictly rejected (no bypass)"""
        # Finalize match
        self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T1"
        }), content_type='application/json')
        
        # Overwrite attempt with override=True
        res = self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T2",
            "override": True
        }), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("already been finalized", data['error'])

    def test_normal_score_overwrite_with_override_true(self):
        """6. Attempted normal score overwrite with override=true is strictly rejected (no bypass)"""
        # Finalize match with normal score
        self.client.post('/update-score', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "score": "15-11",
            "final": True
        }), content_type='application/json')
        
        # Attempt to overwrite finalized score with override=True
        res = self.client.post('/update-score', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "score": "18-20",
            "final": True,
            "override": True
        }), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("already been finalized", data['error'])

    def test_walkover_progression_to_successor(self):
        """Test that winning team advances to the successor match in the tournament bracket"""
        payload = {
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T1"
        }
        res = self.client.post('/declare-walkover', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        
        with app.app_context():
            successor = Match.query.get(2)
            self.assertEqual(successor.team1_id, "T1")

    def test_walkover_does_not_fabricate_scores(self):
        """Test that walkover does not insert fake fabricated score values"""
        payload = {
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T1"
        }
        self.client.post('/declare-walkover', data=json.dumps(payload), content_type='application/json')
        
        with app.app_context():
            scores = Score.query.filter_by(match_id=1).all()
            for s in scores:
                self.assertEqual(s.score, 0)  # Scores remain unmanipulated (0-0)

    def test_get_match_score_includes_walkover(self):
        """Test GET /score/match returns walkover metadata"""
        self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T1"
        }), content_type='application/json')
        
        res = self.client.get('/score/match?match_id=1&tournament_id=1')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['is_walkover'])
        self.assertEqual(data['result_type'], 'walkover')
        self.assertEqual(data['winner_team_id'], 'T1')

    def test_fixtures_endpoint_includes_walkover(self):
        """Test GET /get-match-fixtures reflects walkover outcome without fake numbers"""
        self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T1"
        }), content_type='application/json')
        
        res = self.client.get('/get-match-fixtures?tournament_id=1')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        match1 = next(m for m in data['matches'] if m['match_id'] == 1)
        self.assertEqual(match1['match_result'], 'WALKOVER')
        self.assertTrue(match1['match_status']['is_walkover'])
        self.assertEqual(match1['match_status']['result_type'], 'walkover')
        self.assertEqual(match1['match_status']['winner_team_id'], 'T1')

    def test_model_result_type_and_is_walkover_sync(self):
        """9. Consistency between result_type and is_walkover: validator & event listener synchronization"""
        with app.app_context():
            # In-memory validation
            m = Match(id=99, match_name="Test Sync", round_id="1", pool="A", tournament_id=1)
            m.result_type = 'walkover'
            self.assertTrue(m.is_walkover)

            m.result_type = 'regular'
            self.assertFalse(m.is_walkover)

            # Persisted regular match invariant:
            # status=completed, is_final=True, result_type=regular, is_walkover=False
            m_reg = Match.query.get(1)
            # simulate completed regular
            m_reg.status = 'completed'
            m_reg.is_final = True
            m_reg.result_type = 'regular'
            db.session.commit()
            db.session.refresh(m_reg)
            self.assertEqual(m_reg.status, 'completed')
            self.assertTrue(m_reg.is_final)
            self.assertEqual(m_reg.result_type, 'regular')
            self.assertFalse(m_reg.is_walkover)

            # Persisted walkover match invariant:
            # status=completed, is_final=True, result_type=walkover, is_walkover=True
            m_wo = Match.query.get(2)
            m_wo.status = 'completed'
            m_wo.is_final = True
            m_wo.result_type = 'walkover'
            m_wo.winner_team_id = 'T1'
            db.session.commit()
            db.session.refresh(m_wo)
            self.assertEqual(m_wo.status, 'completed')
            self.assertTrue(m_wo.is_final)
            self.assertEqual(m_wo.result_type, 'walkover')
            self.assertTrue(m_wo.is_walkover)

    def test_successor_match_no_duplicate_scores(self):
        """Test that multiple progression calls do not create duplicate scores in successor"""
        # Declare walkover match 1 -> sets successor (match 2) team1_id
        self.client.post('/declare-walkover', data=json.dumps({
            "match_id": 1,
            "tournament_id": 1,
            "winning_team_id": "T1"
        }), content_type='application/json')

        # Calling update_successor_match again
        with app.app_context():
            from routes.score.score_core import update_successor_match
            update_successor_match(2, 1, "T1")

            successor = Match.query.get(2)
            self.assertEqual(successor.team1_id, "T1")
            scores = Score.query.filter_by(match_id="2").all()
            self.assertLessEqual(len(scores), 2)

    def test_four_team_knockout_bracket_creation_and_fk_integrity(self):
        """10a. Four-team bracket creation without 'TBD' placeholder, satisfying FK integrity"""
        with app.app_context():
            # Setup Tournament 2 and 4 teams
            t2 = Tournament(id=2, tournament_name="Knockout Test Tournament", type="elimination", season_id=1)
            db.session.add(t2)
            for i in range(1, 5):
                team = Team(team_id=f"2_{i}", name=f"Team 2_{i}", tournament_id=2)
                db.session.add(team)
            db.session.commit()

        # Call POST /knockout
        payload = {
            "tournament_id": 2,
            "team_ids": ["2_1", "2_2", "2_3", "2_4"],
            "current_round_id": 1
        }
        res = self.client.post('/knockout', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['matches_created'], 3)
        self.assertEqual(data['starting_round'], 2)
        self.assertEqual(data['total_rounds'], 2)

        with app.app_context():
            # Verify no 'TBD' in round or match tables
            tbd_rounds = Round.query.filter_by(tournament_id=2, team_id='TBD').count()
            self.assertEqual(tbd_rounds, 0)
            
            tbd_matches = Match.query.filter(
                Match.tournament_id == 2,
                (Match.team1_id == 'TBD') | (Match.team2_id == 'TBD')
            ).count()
            self.assertEqual(tbd_matches, 0)

            # Semifinal rounds associated with the 4 actual teams
            sf_rounds = Round.query.filter_by(tournament_id=2, round_id=2).all()
            sf_team_ids = {r.team_id for r in sf_rounds}
            self.assertEqual(sf_team_ids, {"2_1", "2_2", "2_3", "2_4"})

            # Future round descriptor has team_id=None (nullable)
            final_rounds = Round.query.filter_by(tournament_id=2, round_id=3).all()
            self.assertEqual(len(final_rounds), 1)
            self.assertIsNone(final_rounds[0].team_id)
            self.assertEqual(final_rounds[0].name, "Finals")

            # Verify matches
            sf1 = Match.query.filter_by(tournament_id=2, round_id="2", bracket_position=0).first()
            sf2 = Match.query.filter_by(tournament_id=2, round_id="2", bracket_position=1).first()
            final_match = Match.query.filter_by(tournament_id=2, round_id="3", bracket_position=0).first()

            self.assertIsNotNone(sf1)
            self.assertIsNotNone(sf2)
            self.assertIsNotNone(final_match)

            self.assertEqual(sf1.team1_id, "2_1")
            self.assertEqual(sf1.team2_id, "2_2")
            self.assertEqual(sf2.team1_id, "2_3")
            self.assertEqual(sf2.team2_id, "2_4")

            # Final match participants are unassigned (None)
            self.assertIsNone(final_match.team1_id)
            self.assertIsNone(final_match.team2_id)

            # Predecessors and successors
            self.assertEqual(sf1.successor, final_match.id)
            self.assertEqual(sf2.successor, final_match.id)
            self.assertEqual(final_match.predecessor_1, sf1.id)
            self.assertEqual(final_match.predecessor_2, sf2.id)

    def test_both_semifinal_winners_progress_into_final(self):
        """10b. Walkover in both semifinals progresses winners into final's predecessor_1 and predecessor_2 slots"""
        with app.app_context():
            # Setup Tournament 3 and 4 teams
            t3 = Tournament(id=3, tournament_name="Knockout Progression Test", type="elimination", season_id=1)
            db.session.add(t3)
            for i in range(1, 5):
                team = Team(team_id=f"3_{i}", name=f"Team 3_{i}", tournament_id=3)
                db.session.add(team)
            db.session.commit()

        # Generate bracket
        res = self.client.post('/knockout', data=json.dumps({
            "tournament_id": 3,
            "team_ids": ["3_1", "3_2", "3_3", "3_4"],
            "current_round_id": 1
        }), content_type='application/json')
        self.assertEqual(res.status_code, 201)

        with app.app_context():
            sf1 = Match.query.filter_by(tournament_id=3, round_id="2", bracket_position=0).first()
            sf2 = Match.query.filter_by(tournament_id=3, round_id="2", bracket_position=1).first()
            final_match = Match.query.filter_by(tournament_id=3, round_id="3", bracket_position=0).first()
            sf1_id, sf2_id, final_id = sf1.id, sf2.id, final_match.id

        # 1. Declare Walkover on SF1 with winning team "3_1"
        res_sf1 = self.client.post('/declare-walkover', data=json.dumps({
            "match_id": sf1_id,
            "tournament_id": 3,
            "winning_team_id": "3_1"
        }), content_type='application/json')
        self.assertEqual(res_sf1.status_code, 200)

        with app.app_context():
            final_match = Match.query.get(final_id)
            self.assertEqual(final_match.team1_id, "3_1")  # Slot 1 populated from predecessor_1 (SF1)
            self.assertIsNone(final_match.team2_id)  # Slot 2 still unassigned

        # 2. Declare Walkover on SF2 with winning team "3_4"
        res_sf2 = self.client.post('/declare-walkover', data=json.dumps({
            "match_id": sf2_id,
            "tournament_id": 3,
            "winning_team_id": "3_4"
        }), content_type='application/json')
        self.assertEqual(res_sf2.status_code, 200)

        with app.app_context():
            final_match = Match.query.get(final_id)
            self.assertEqual(final_match.team1_id, "3_1")  # Slot 1
            self.assertEqual(final_match.team2_id, "3_4")  # Slot 2 populated from predecessor_2 (SF2)

            # Scores for Final match automatically initialized for both teams
            scores = Score.query.filter_by(match_id=final_id).all()
            self.assertEqual(len(scores), 2)
            score_teams = {s.team_id for s in scores}
            self.assertEqual(score_teams, {"3_1", "3_4"})

            # Round table for Finals (round_id=3) now associated with both finalists
            final_round_teams = {r.team_id for r in Round.query.filter_by(tournament_id=3, round_id=3).all() if r.team_id}
            self.assertEqual(final_round_teams, {"3_1", "3_4"})

if __name__ == '__main__':
    unittest.main()
