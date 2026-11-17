"""Cookbook rendering and native-token accounting, without service calls."""

from __future__ import annotations

from datetime import datetime
import warnings

from tinker_cookbook.renderers.gpt_oss import GptOssRenderer
from tinker_cookbook.renderers.qwen3 import Qwen3DisableThinkingRenderer
from .prompts import get_tokenizer, messages


class Rendering:
    def __init__(self, model: str, config: dict):
        self.model = model
        self.tokenizer = get_tokenizer(model)
        self.date = config["reference_template_date"]
        if model == config["primary_model"]:
            self.renderer = Qwen3DisableThinkingRenderer(self.tokenizer)
        elif model == config["reference_model"]:
            self.renderer = GptOssRenderer(
                self.tokenizer,
                use_system_prompt=True,
                reasoning_effort=config["reference_reasoning_effort"],
                current_date=self.date,
            )
        else:
            raise ValueError("Model is outside the approved evaluation.")
        vocab = self.tokenizer.get_vocab()
        self.special = {
            token: vocab[token]
            for token in (
                "<think>",
                "</think>",
                "<|start|>",
                "<|end|>",
                "<|channel|>",
                "<|message|>",
                "<|im_start|>",
                "<|im_end|>",
            )
            if token in vocab
        }

    def native_ids(self, public_messages: list[dict]) -> list[int]:
        date = datetime.strptime(self.date, "%Y-%m-%d")
        return self.tokenizer.apply_chat_template(
            public_messages,
            tokenize=True,
            add_generation_prompt=True,
            enable_thinking=False,
            strftime_now=lambda pattern: date.strftime(pattern),
        )

    def prompt(self, public_messages: list[dict]):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="use_system_prompt=True but messages already"
            )
            rendered = self.renderer.build_generation_prompt(public_messages)
        if rendered.to_ints() != self.native_ids(public_messages):
            raise ValueError("Cookbook/native token mismatch. No sample was submitted.")
        return rendered

    def observation(self, record: dict, turns: list[dict]):
        return self.prompt(messages(record, turns))

    def decode(self, tokens: list[int]) -> dict:
        """Count sampled token spans; framing tokens have their own bucket."""
        tokenizer = self.tokenizer
        raw = tokenizer.decode(tokens, skip_special_tokens=False)
        parsed, termination = self.renderer.parse_response(tokens)
        content = parsed["content"]
        if isinstance(content, str):
            action = content
        else:
            action = "".join(p["text"] for p in content if p["type"] == "text")
        stop_ids = set(self.renderer.get_stop_sequences())
        special = self.special
        reasoning = action_count = control = 0
        action_ids = []
        thinking = False
        header: list[int] | None = None
        for token in tokens:
            if self.model.startswith("Qwen/"):
                if token == special.get("<think>"):
                    thinking = True
                    control += 1
                elif token == special.get("</think>"):
                    thinking = False
                    control += 1
                elif token in stop_ids:
                    control += 1
                elif thinking:
                    reasoning += 1
                else:
                    action_count += 1
            elif token == special.get("<|channel|>"):
                header = []
                control += 1
            elif token == special.get("<|start|>"):
                header = []
                control += 1
            elif token == special.get("<|message|>"):
                channel = tokenizer.decode(header or []).strip()
                thinking = "analysis" in channel.split()
                header = None
                control += 1
            elif token in stop_ids or token == special.get("<|end|>"):
                control += 1
            elif header is not None:
                header.append(token)
                control += 1
            elif thinking:
                reasoning += 1
            else:
                action_count += 1
                action_ids.append(token)
        if self.model.startswith("openai/"):
            # Truncated Harmony responses fall back to raw framing in the
            # cookbook parser. Only generated non-analysis content is an action.
            action = tokenizer.decode(action_ids, skip_special_tokens=False)
        return {
            "action": action,
            "raw_model_text": raw,
            "reasoning_tokens": reasoning,
            "action_tokens": action_count,
            "control_tokens": control,
            "parse_termination": str(termination),
        }
