# Notes for the later write-up

These are observations and hypotheses to revisit, not changes to the experiment.

- Gambling: A11 frequently guesses with multiple candidates remaining at large N, including games with unused question budget. The main curriculum allocates only 32 games to N=128, compared with 88 at N=16. Limited large-N exposure is a possible cause, stated as a hypothesis; this allocation has not been manipulated, so the current data do not establish causality. Keep the curriculum and rewards unchanged for A23/B41.
- Sampler versus trainer log probabilities: A11's largest absolute generated-token gap was 2.703809 nats. Update-mean differences ranged from -0.018563 to +0.004860 nats. Native token sequences matched; the backend cause is unestablished. Disclose this diagnostic and record the same numbers for later seeds. Do not present it as a proven explanation for any behavioral result.
- The approved suffix-tolerant re-evaluation is auxiliary only. Its results must be labelled alongside, never substituted for, the primary A11 scores. New answers change later candidate feedback and model actions; this is a fresh rollout diagnostic, not post-hoc rescoring.

## A11 checkpoint availability correction

A11 suffix diagnostic and hard mode: **not run: A11 checkpoint wasn't persisted, external uploads unavailable**. The local adapter and hashes remain an archive. Sixteen failed diagnostic requests produced no usable output and retain $0.023700 in original holds. These are excluded and will not be replaced. The same labelled suffix diagnostic and hard-mode comparison run immediately on A23's permanent native endpoint. Native no-expiry training and sampler saves are verified in a throwaway session before A23.
