# Replay viewer

Open index.html directly, or serve the repository with `python3 -m http.server 8765` and visit `http://localhost:8765/replays/`.

Play, step with the arrow buttons, scrub the timeline, switch noise settings, or hide the target. Load match accepts the JSON schema in games.json. Model traces later use the same record and turns fields. The two players must share a record and target.

The examples were selected to show a visible contrast, and the noisy example includes a re-check. They are illustrations, not a performance sample. The complete baseline grid supplies the reported numbers. In noisy mode cell shading represents posterior weight. A candidate is eliminated only when its posterior is exactly zero.

The viewer uses locally bundled Manrope and Instrument Serif fonts under their included OFL licenses, and the locally bundled GSAP runtime. Exports have no audio. See scripts/export_replays.py for a reproducible local export.
