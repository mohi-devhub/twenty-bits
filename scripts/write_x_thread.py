"""Validate and format a copy-ready draft, without publishing anything."""

import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT


def main():
    draft = json.loads((ROOT / "research/x_thread_draft.json").read_text())
    posts = draft["posts"]
    assert 6 <= len(posts) <= 8
    lines = [
        "# X thread draft",
        "",
        "For user review only. Nothing has been posted. Text blocks are the posts; media and source notes are outside them.",
        "",
    ]
    if draft["repo_url"] == "[REPO_URL]":
        lines += [
            "Replace `[REPO_URL]` with the public repository URL before posting. This checkout has no configured Git remote.",
            "",
        ]
    counts = []
    for index, post in enumerate(posts, 1):
        text = f"{index}/{len(posts)} " + post["text"].replace(
            "[REPO_URL]", draft["repo_url"]
        )
        assert not re.search(r"\b(first|novel)\b|[—–]", text, re.I)
        weighted = re.sub(r"https?://\S+", "x" * 23, text)
        assert len(weighted) <= 280, (index, len(weighted))
        assert (ROOT / post["source"]).exists()
        if post["media"]:
            # Outputs are checked by the write-up verifier after local rendering.
            media = f"[{Path(post['media']).name}]({post['media']})"
        else:
            media = "None. Repository link only."
        counts.append(len(weighted))
        lines += [
            f"## Post {index}",
            "",
            "```text",
            text,
            "```",
            "",
            f"Media: {media}",
            "",
            f"Source: [{post['source']}]({post['source']}). Length: {len(weighted)} characters under URL weighting.",
            "",
        ]
    (ROOT / "X_THREAD.md").write_text("\n".join(lines))
    print(
        json.dumps({"posts": len(posts), "character_counts": counts, "posted": False})
    )


if __name__ == "__main__":
    main()
