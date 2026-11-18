# Native checkpoint API verification

The account-wide `GET /api/v1/checkpoints` listing returned five checkpoints. Both exact test paths are present. Below are the requested fields, preserving their API values. No browser was used.

```json
[
  {
    "checkpoint_id": "sampler_weights/persistence-smoke-20261119",
    "tinker_path": "tinker://0bf5f21e-507e-50ac-94f6-50cb387aa043:train:0/sampler_weights/persistence-smoke-20261119",
    "size_bytes": 369266765,
    "expires_at": null
  },
  {
    "checkpoint_id": "weights/persistence-smoke-20261119",
    "tinker_path": "tinker://0bf5f21e-507e-50ac-94f6-50cb387aa043:train:0/weights/persistence-smoke-20261119",
    "size_bytes": 1107556469,
    "expires_at": null
  }
]
```

The source save session was already finished. After listing the files, a fresh service client loaded the listed sampler path and returned `READY.<|im_end|>`: three generated tokens, **$0.000006**. Its request ID was saved before dispatch and its result is collected and settled. The fresh session has also finished.

Fresh session: `75be327f-297d-5e99-9578-f625990f71d6`. Sample request: `75be327f-297d-5e99-9578-f625990f71d6:sample:0:0`.

Both test files remain saved for the user to cross-check in the console. No test file was deleted, and no Pixel Miser checkpoint was changed. A23 and B41 have not started. A23 still requires the user's explicit console confirmation; API success does not clear that gate.

Project usage **$11.015862**, holds **$1.131236**, available **$37.852902** under the $50 cap. All existing holds remain. The two smoke samples together cost $0.000012; the test-storage reserve remains $0.640002 pending billing.

Validation: real account-wide listing, exact-path/type/size/expiry checks, a real fresh-client sample, matching pre-dispatch request ID and receipt, and no pending HTTP work. Existing science settings, frozen games and primary code are unchanged.

[Exact API evidence](research/native_persistence_api_verification.json), [guarded verification script](scripts/verify_native_checkpoint_api.py), [prior persistence correction](CHECKPOINT_PERSISTENCE.md).
