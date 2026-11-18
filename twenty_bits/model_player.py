"""The exact game behind cookbook Env and TokenCompleter interfaces."""

from __future__ import annotations

import tinker
from tinker_cookbook.completers import TokenCompleter, TokensWithLogprobs
from tinker_cookbook.rl.types import Env, InitialObservationOverflow, StepResult

from .game import Game
from .tinker_rendering import Rendering
from .worlds import seed_for


class TableEnv(Env):
    def __init__(self, record: dict, model: str, config: dict, *, message_builder=None):
        self.game = Game(record)
        self.model = model
        self.config = config
        self.rendering = Rendering(model, config)
        self.output_cap = config[
            "primary_output_cap"
            if model == config["primary_model"]
            else "reference_output_cap"
        ]
        self.last_sample = None
        self.usage = []
        self.context_overflow = False
        self.message_builder = message_builder

    def observation(self):
        if self.message_builder is not None:
            return self.rendering.prompt(
                self.message_builder(self.game.record, self.game.turns)
            )
        return self.rendering.observation(self.game.record, self.game.turns)

    def overflow(self):
        self.context_overflow = True
        self.game.done = True

    async def initial_observation(self):
        observation = self.observation()
        if observation.length + self.output_cap > self.config["context_window"]:
            self.overflow()
            return InitialObservationOverflow(reward=0, metrics={"stop/max_tokens": 1})
        return observation, self.rendering.renderer.get_stop_sequences()

    async def step(self, action, *, extra=None):
        decoded = self.rendering.decode(action)
        text = decoded["action"]
        predicate_tokens = None
        if text.strip().startswith("ASK: "):
            predicate_tokens = len(
                self.rendering.tokenizer.encode(
                    text.strip()[5:].strip(),
                    add_special_tokens=False,
                )
            )
        reward_before = self.game.reward
        turn = self.game.step(
            text,
            reasoning_tokens=decoded["reasoning_tokens"],
            action_tokens=decoded["action_tokens"],
            predicate_tokens=predicate_tokens,
            truncated=(extra or {}).get("stop_reason") == "length",
        )
        turn.update({k: v for k, v in decoded.items() if k != "action"})
        if self.last_sample is not None:
            turn["usage"] = self.last_sample
            self.usage.append(self.last_sample)
        observation = (
            tinker.ModelInput.empty() if self.game.done else self.observation()
        )
        if (
            not self.game.done
            and observation.length + self.output_cap > self.config["context_window"]
        ):
            self.overflow()
            observation = tinker.ModelInput.empty()
        return StepResult(
            reward=self.game.reward - reward_before,
            episode_done=self.game.done,
            next_observation=observation,
            next_stop_condition=self.rendering.renderer.get_stop_sequences(),
            metrics={"eig": turn["eig"], "stop/completed": int(self.game.done)},
        )

    def result(self):
        result = self.game.result()
        result.update(
            model=self.model,
            policy="base",
            context_overflow=self.context_overflow,
            turns=self.game.turns,
            sampling_calls=len(self.usage),
            prompt_tokens=sum(u["prompt_tokens"] for u in self.usage),
            output_tokens=sum(u["output_tokens"] for u in self.usage),
            prompt_cache_hit_tokens=sum(
                u["prompt_cache_hit_tokens"] for u in self.usage
            ),
            predicate_tokens=sum(
                t["predicate_tokens"] or 0 for t in self.game.turns if t["is_question"]
            ),
            control_tokens=sum(t["control_tokens"] for t in self.game.turns),
        )
        return result


class GuardedCompleter(TokenCompleter):
    def __init__(self, transport, env: TableEnv):
        self.transport = transport
        self.env = env

    async def __call__(self, model_input, stop, *, max_tokens=None):
        env = self.env
        cap = env.output_cap
        if max_tokens is not None and max_tokens != cap:
            raise ValueError("A rollout attempted to change the frozen output cap.")
        turn = len(env.game.turns)
        seed = seed_for(
            env.config["sampling_seed_namespace"], env.game.record["id"], turn
        ) % (2**31)
        params = tinker.SamplingParams(
            max_tokens=cap,
            seed=seed,
            stop=stop,
            temperature=env.config["temperature"],
            top_p=env.config["top_p"],
            top_k=env.config["top_k"],
        )
        journal = await self.transport.sample(
            model=env.model,
            key=f"{env.model}/{env.game.record['id']}/turn-{turn}",
            prompt=model_input,
            params=params,
        )
        sequence = journal["response"]["sequences"][0]
        env.last_sample = {
            k: journal[k]
            for k in (
                "entry_id",
                "prompt_tokens",
                "output_tokens",
                "prompt_cache_hit_tokens",
                "actual_usd",
            )
        }
        env.last_sample["request_id"] = journal["receipt"]["request_id"]
        sequence_ids = journal["receipt"].get("sample_sequence_ids")
        return TokensWithLogprobs(
            tokens=sequence["tokens"],
            maybe_logprobs=sequence.get("logprobs"),
            stop_reason=sequence["stop_reason"],
            sequence_id=sequence_ids[0] if sequence_ids else None,
            prompt_cache_hit_tokens=journal["prompt_cache_hit_tokens"],
        )
