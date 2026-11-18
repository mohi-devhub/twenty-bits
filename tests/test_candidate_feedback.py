"""Public state feedback, including exact threshold boundaries and noisy reentry."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from twenty_bits.budget import CAP, Ledger
from twenty_bits.candidate_feedback import candidate_messages, feedback, feedback_text
from twenty_bits.game import Game
from twenty_bits.learnability import probe_messages
from twenty_bits.worlds import training_game

PAID_AVAILABLE = all(
    importlib.util.find_spec(name) is not None for name in ("tinker", "httpx")
)
if PAID_AVAILABLE:
    import httpx
    from tinker._client import AsyncTinker
    from twenty_bits.tinker_transport import GuardedTinker


class CandidateFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.record = training_game(4, 600000, seed=20261120, noise=0)

    def test_exact_support_in_original_order(self):
        names = self.record["world"]["names"]
        state = feedback(self.record, [0, 0.5, 0, 0.5])
        self.assertEqual(state, {"kind": "exact", "candidates": [names[1], names[3]]})

    def test_noisy_threshold_is_strict_and_top_is_included(self):
        self.record["noise"] = 0.1
        state = feedback(self.record, [0.001, 0.009, 0.99, 0])
        names = self.record["world"]["names"]
        self.assertEqual(state["candidates"], [names[1], names[2]])
        self.assertEqual(state["top_candidate"], names[2])
        wide = {"noise": 0.1, "world": {"names": [f"x{i}" for i in range(2000)]}}
        low = feedback(wide, [1 / 2000] * 2000)
        self.assertEqual(low["candidates"], ["x0"])
        self.assertEqual(low["top_candidate"], "x0")

    def test_noisy_candidates_can_reenter(self):
        self.record["noise"] = 0.1
        names = self.record["world"]["names"]
        self.assertNotIn(
            names[0], feedback(self.record, [0.0001, 0.4999, 0.25, 0.25])["candidates"]
        )
        self.assertIn(
            names[0], feedback(self.record, [0.002, 0.498, 0.25, 0.25])["candidates"]
        )

    def test_each_answer_gets_its_own_state_without_changing_prior_messages(self):
        game = Game(self.record)
        game.step("ASK: " + game.world.attributes[0])
        game.step("ASK: impossible_unknown_attribute")
        original = probe_messages(self.record, game.turns)
        public = candidate_messages(self.record, game.turns)
        self.assertTrue(public[3]["content"].startswith(game.turns[0]["answer"] + "\n"))
        self.assertTrue(public[5]["content"].startswith("INVALID\n"))
        self.assertEqual(
            public[3]["content"].split("\n", 1)[1],
            public[5]["content"].split("\n", 1)[1],
        )
        self.assertEqual(probe_messages(self.record, game.turns), original)
        self.assertEqual(public[2], original[2])

    def test_target_does_not_enter_feedback(self):
        game = Game(self.record)
        game.step("ASK: " + game.world.attributes[0])
        changed = copy.deepcopy(self.record)
        changed["target"] = (changed["target"] + 1) % changed["n"]
        self.assertEqual(
            candidate_messages(changed, game.turns),
            candidate_messages(self.record, game.turns),
        )

    def test_table_prefix_is_stable_across_turns_and_noise(self):
        game = Game(self.record)
        before = candidate_messages(self.record)[0]
        game.step("ASK: " + game.world.attributes[0])
        self.assertEqual(candidate_messages(self.record, game.turns)[0], before)
        changed = {**self.record, "noise": 0.1}
        self.assertEqual(candidate_messages(changed)[0], before)

    def test_invalid_posteriors_are_rejected(self):
        for posterior in ([0, 0, 0, 0], [1, 0], [-1, 1, 1, 0], [float("nan"), 0, 0, 1]):
            with self.subTest(posterior=posterior), self.assertRaises(ValueError):
                feedback(self.record, posterior)

    def test_noisy_text_discloses_approximation_and_top(self):
        self.record["noise"] = 0.1
        state = feedback(self.record, [0.25] * 4)
        text = feedback_text(state)
        self.assertIn("probability > 0.001", text)
        self.assertIn("TOP CANDIDATE: " + self.record["world"]["names"][0], text)


@unittest.skipUnless(
    PAID_AVAILABLE, "Install .[paid] for mocked checkpoint-sampler tests."
)
class CheckpointSamplerTests(unittest.IsolatedAsyncioTestCase):
    async def test_checkpoint_and_raw_base_requests_use_guarded_metadata(self):
        for checkpoint in (
            None,
            "tinker://existing:train:0/sampler_weights/format-warmstart",
        ):
            with (
                self.subTest(checkpoint=checkpoint),
                tempfile.TemporaryDirectory() as folder,
            ):
                directory = Path(folder)
                path = directory / "ledger.json"
                path.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "cap_usd": str(CAP),
                            "reservation_multiplier": "1.5",
                            "entries": [],
                            "blocks": [],
                        }
                    )
                )
                requests = []

                def respond(request):
                    requests.append(json.loads(request.content))
                    return httpx.Response(
                        200, json={"sampling_session_id": "unit:sample:0"}
                    )

                client = AsyncTinker(
                    api_key="tml-unit-key",
                    base_url="https://unit.invalid",
                    max_retries=0,
                    http_client=httpx.AsyncClient(
                        transport=httpx.MockTransport(respond)
                    ),
                )
                transport = GuardedTinker(
                    {
                        "run_id": "unit",
                        "sampling_checkpoint_paths": {"model": checkpoint}
                        if checkpoint
                        else {},
                    },
                    directory / "run",
                    ledger=Ledger(path),
                    usage_path=directory / "usage.jsonl",
                    run_cap_usd=".25",
                )
                transport.client = client
                transport.state["session_id"] = "unit"
                sampler = await transport.sampler("model")
                self.assertEqual(requests[0].get("model_path"), checkpoint)
                self.assertEqual(requests[0]["base_model"], "model")
                self.assertEqual(sampler.get("model_path"), checkpoint)
                self.assertEqual(await transport.sampler("model"), sampler)
                self.assertEqual(len(requests), 1)
                self.assertEqual(
                    transport.ledger.status()["entries"][0]["state"], "settled"
                )
                await transport.close()


if __name__ == "__main__":
    unittest.main()
