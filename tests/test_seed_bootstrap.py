import unittest

try:
    from scripts.analyze_A23_replication import across_seed_intervals
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "paid analysis extras are optional")
class SeedBootstrapTests(unittest.TestCase):
    def games(self, eig):
        return [{"domain":"animals", "n":32, "noise":0, "game_id":str(i),
                 "won":i%2==0, "questions":1, "question_eigs":[eig]} for i in range(28)]

    def test_identical_endpoints_have_zero_paired_change(self):
        # Duplicate the cell for the synthetic subset required by the reporter.
        raw=self.games(1)
        raw += [{**g,"domain":"synthetic","game_id":"s"+g["game_id"]} for g in raw]
        result=across_seed_intervals(raw,{11:raw,23:raw},[("animals",32,0),("synthetic",32,0)],draws=200)
        for subset in result["ci95_mean_A_endpoint_minus_raw"].values():
            self.assertEqual(subset["eig_per_question"],[0,0])
            self.assertEqual(subset["win_rate"],[0,0])

    def test_two_different_seeds_contribute_to_interval(self):
        raw=self.games(1)
        raw += [{**g,"domain":"synthetic","game_id":"s"+g["game_id"]} for g in raw]
        final={11:[{**g,"question_eigs":[.5]} for g in raw],
               23:[{**g,"question_eigs":[0]} for g in raw]}
        result=across_seed_intervals(raw,final,[("animals",32,0),("synthetic",32,0)],draws=200)
        self.assertEqual(result["ci95_mean_A_endpoint_minus_raw"]["noiseless_animals"]["eig_per_question"],[-1,-.5])
