# Native endpoint persistence

The A11 suffix diagnostic and A11 hard mode are **not run: A11 checkpoint wasn't persisted, external uploads unavailable**. A11's completed primary evaluation remains unchanged. Its local adapter and SHA-256 hashes are an archive only. The local file is not a usable hosted checkpoint on this account.

The earlier two-hour sampler/export saves expired, and the source service session was finished. Sampler metadata still existed, but requests through that session were rejected. Metadata did not establish that sampling remained possible. External upload was explicitly rejected before any file upload. Sixteen diagnostic turns produced no usable output, are permanently excluded, and retain $0.023700 in original holds. No diagnostic game completed and none of those outputs entered training or evaluation.

The replacement uses named native **training** and **sampler** checkpoints with `ttl_seconds=None`. The scheduled A23 and B41 endpoints keep both types without expiry. Their paths, sizes, expiry fields and storage reserves are written into the ledger. No external upload is needed.

The throwaway test saved Qwen3-8B rank-32 native files without an optimizer update: training state **1,107,556,469 bytes**, sampler weights **369,266,765 bytes**. Both API records have `expires_at: null`. After finishing the source session, a fresh service client loaded the native sampler path and returned `READY.` for **$0.000006**. Console verification and deletion are recorded in [the test evidence](research/native_persistence_test.json). A23 cannot start until both are complete.

The test reserves a conservative full day at 64 GB per checkpoint, including 1.5x margin: **$0.640002** held until billing reconciliation. Deletion does not release unknown charges. Main endpoint storage reserves cover 30 days, using twice the measured test bytes and the normal 1.5x margin. At measured sizes, one endpoint pair would cost **$0.147682/month** on the paid plan. These are ongoing native files: no expiry is set. Future months must remain visible in budget reconciliation; a storage reserve is not a settled bill.

The paid storage bound is **$0.10 per decimal GB per month**. The documented free plan covers up to 100 GB or 100 checkpoints per organization, whichever limit is reached sooner. This project does not change the organization's billing plan or rely on a zero storage bill. [Tinker storage documentation](https://tinker-docs.thinkingmachines.ai/administration/checkpoint-storage-pricing/).

The test cleanup accepts only its exact newly created model ID and `persistence-smoke-20261119` paths. Pixel Miser checkpoints are outside that allowlist. A23 runs its frozen primary evaluation, suffix diagnostic and hard-mode comparison immediately after training, then stops before B41.

The user subsequently selected SDK/API-only verification and will check the console personally. The account-wide API listing confirms both test files, and a second fresh client successfully sampled from the listed sampler path. This additional sample cost $0.000006, bringing total smoke sampling to $0.000012. Both files remain intact until the user confirms the console. See [the exact-field API gate](CHECKPOINT_API_GATE.md). No browser access occurred.
