/* Saved game state drives every visible value; the animation clock adds no game logic. */
(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const panels = [$("#left"), $("#right")];
  let pairs = window.REPLAYS;
  let selected =
    window.REPLAY_EXAMPLE ??
    Number(new URLSearchParams(location.search).get("example") || 0);
  let step = 0;
  let timeline;
  const exportMode =
    window.REPLAY_EXPORT ||
    new URLSearchParams(location.search).get("export") === "1";
  if (exportMode) document.body.classList.add("export");
  const titleName = (name) =>
    name.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
  function describe(name) {
    const match = name.match(/^(adult|juvenile)_(female|male)_(.*)$/);
    return match
      ? [titleName(match[3]), titleName(match[1] + "_" + match[2])]
      : [titleName(name), ""];
  }
  function renderStep(value) {
    step = Math.max(0, Math.min(Math.floor(value), maxSteps()));
    const pair = pairs[selected];
    const reveal = $("#reveal").checked;
    $("#scrubber").value = step;
    $("#step-label").textContent = `Turn ${step}`;
    $("#back").disabled = step === 0;
    $("#next").disabled = step === maxSteps();
    $("#target-name").textContent = reveal
      ? titleName(pair.record.world.names[pair.record.target])
      : "Hidden";
    pair.players.forEach((player, index) => {
      const panel = panels[index];
      const trace = player.trace;
      const completed = Math.min(step, trace.turns.length);
      const turn = completed ? trace.turns[completed - 1] : null;
      const posterior = turn
        ? turn.posterior_after
        : pair.record.world.names.map(() => 1 / pair.record.n);
      const max = Math.max(...posterior);
      const h = -posterior.reduce((s, p) => s + (p ? p * Math.log2(p) : 0), 0);
      $(".remaining", panel).textContent = pair.record.noise
        ? (2 ** h).toFixed(1)
        : posterior.filter((p) => p > 0).length;
      $(".population-label", panel).textContent = pair.record.noise
        ? "effective candidates"
        : "candidates remain";
      [...$(".candidate-grid", panel).children].forEach((cell, i) => {
        cell.classList.toggle("eliminated", posterior[i] === 0);
        cell.classList.toggle(
          "target-cell",
          reveal && i === pair.record.target,
        );
        cell.style.setProperty(
          "--mass",
          pair.record.noise
            ? Math.sqrt(posterior[i] / max)
            : Number(posterior[i] > 0),
        );
        cell.title = `${titleName(pair.record.world.names[i])} — posterior ${(posterior[i] * 100).toFixed(3)}%`;
      });
      $(".turn-type", panel).textContent = turn
        ? turn.is_question
          ? `QUESTION ${turn.questions_used}`
          : "FINAL GUESS"
        : "READY TO SEARCH";
      $(".question", panel).textContent = turn
        ? turn.action
        : "Every candidate is equally likely.";
      $(".answer", panel).textContent = turn ? turn.answer : "—";
      $(".surprise", panel).textContent = turn?.reask_after_low_probability
        ? "Re-check after an unlikely reply"
        : turn?.low_probability_answer
          ? `Unlikely reply · ${(turn.answer_probability * 100).toFixed(1)}% predicted`
          : turn?.flipped
            ? "Answer flipped by the seeded noise channel"
            : "";
      const questions = trace.turns
        .slice(0, completed)
        .filter((t) => t.is_question);
      $(".question-count", panel).textContent =
        `${questions.length} / ${2 * Math.ceil(Math.log2(pair.record.n))}`;
      $(".eig", panel).textContent = questions.length
        ? `${(questions.reduce((s, t) => s + t.eig, 0) / questions.length).toFixed(3)} bits`
        : "—";
      const finished = completed === trace.turns.length;
      $(".outcome", panel).textContent = finished
        ? trace.won
          ? "Correct guess"
          : "Wrong guess"
        : "In progress";
      $(".outcome", panel).classList.toggle("won", finished && trace.won);
    });
  }
  function maxSteps() {
    return Math.max(
      ...pairs[selected].players.map((p) => p.trace.turns.length),
    );
  }
  function loadPair() {
    const pair = pairs[selected];
    if (!pair || pair.players.length !== 2)
      throw new Error("Choose a saved match containing two players.");
    $("#example").value = selected;
    $("#scenario-label").textContent = pair.record.noise
      ? "Independent answer flips · p = 0.10"
      : "Truthful answers · p = 0";
    $("#legend").textContent = pair.record.noise
      ? "Cell shading shows posterior weight. No candidate is ruled out under noise."
      : "Grey candidates are ruled out by the answers. The outlined candidate is the target.";
    $("#ceiling").textContent = `${pair.record.noise ? "0.531" : "1.000"} bits`;
    $("#scrubber").max = maxSteps();
    panels.forEach((panel, i) => {
      $(".policy-name", panel).textContent = pair.players[i].label;
      $(".policy-type", panel).textContent = [
        "random",
        "greedy_single",
        "greedy_predicate",
      ].includes(pair.players[i].trace.policy)
        ? `BASELINE ${i ? "B" : "A"}`
        : `PLAYER ${i ? "B" : "A"}`;
      const grid = $(".candidate-grid", panel);
      grid.replaceChildren();
      pair.record.world.names.forEach((name) => {
        const [main, detail] = describe(name);
        const cell = document.createElement("div");
        cell.className = "candidate";
        const label = document.createElement("span");
        label.className = "candidate-name";
        label.textContent = main;
        const sub = document.createElement("span");
        sub.className = "candidate-detail";
        sub.textContent = detail;
        cell.append(label, sub);
        grid.append(cell);
      });
      grid.style.gridTemplateColumns = `repeat(${pair.record.n <= 32 ? 4 : 8}, minmax(0, 1fr))`;
    });
    timeline?.kill();
    const clock = { t: 0 };
    timeline = gsap.timeline({
      paused: true,
      onComplete: () => {
        $("#play").textContent = "Replay again";
      },
    });
    timeline.to(clock, {
      t: 22,
      duration: 22,
      ease: "none",
      onUpdate: () => renderStep(clock.t / 2),
    });
    window.__timelines = window.__timelines || {};
    window.__timelines.replay = timeline;
    renderStep(0);
    $("#play").textContent = "Play replay";
  }
  window.setReplayTime = (seconds) => {
    timeline.pause();
    timeline.seek(seconds, false);
  };
  window.setReplayExample = (index) => {
    selected = index;
    loadPair();
  };
  $("#play").onclick = () => {
    if (timeline.isActive()) {
      timeline.pause();
      $("#play").textContent = "Continue";
    } else {
      if (timeline.time() >= 2 * maxSteps()) timeline.time(0);
      timeline.play();
      $("#play").textContent = "Pause replay";
    }
  };
  function scrub(value) {
    timeline.pause();
    timeline.seek(2 * value, false);
    renderStep(value);
    $("#play").textContent = "Continue";
  }
  $("#back").onclick = () => scrub(step - 1);
  $("#next").onclick = () => scrub(step + 1);
  $("#scrubber").oninput = (event) => scrub(Number(event.target.value));
  $("#example").onchange = (event) => {
    selected = Number(event.target.value);
    loadPair();
  };
  $("#reveal").onchange = () => renderStep(step);
  document.addEventListener("keydown", (event) => {
    if (["INPUT", "SELECT", "BUTTON"].includes(event.target.tagName)) return;
    if (event.key === "ArrowRight") {
      event.preventDefault();
      scrub(step + 1);
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      scrub(step - 1);
    }
    if (event.key === " ") {
      event.preventDefault();
      $("#play").click();
    }
  });
  $("#import").onchange = async (event) => {
    try {
      const incoming = JSON.parse(await event.target.files[0].text());
      const list = Array.isArray(incoming) ? incoming : [incoming];
      list.forEach((pair) => {
        if (
          !Array.isArray(pair.record?.world?.names) ||
          pair.players?.length !== 2 ||
          pair.players.some((p) => !Array.isArray(p.trace?.turns))
        )
          throw new Error(
            "The file must contain matched records and two saved player traces.",
          );
      });
      pairs = list;
      $("#example").replaceChildren(
        ...pairs.map((pair, i) => {
          const o = document.createElement("option");
          o.value = i;
          o.textContent = pair.label || `Match ${i + 1}`;
          return o;
        }),
      );
      selected = 0;
      loadPair();
      $("#error").hidden = true;
    } catch (error) {
      $("#error").textContent = `Could not load match: ${error.message}`;
      $("#error").hidden = false;
    }
  };
  loadPair();
})();
