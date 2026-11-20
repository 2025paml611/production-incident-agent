# Why the six agents decide differently

Every agent receives the same selected scenario. The comparison below is the
assignment table for scenarios A–D.

The five classical actions were produced by running those agents on
`data/scenarios/scenarios.json` with the seeded file
`data/learning/experience.json`. The Local Ollama LLM actions are the ones
already captured in `screenshots/`. That model is not re-run by this document,
and a later Ollama run can word the same evidence differently. Confidence
values are agent-reported and are not calibrated probabilities.

The Streamlit page prints the same kind of explanation after **Compare all six
agents**, using whatever each agent returned on that run.

## Scenario A — database pool exhausted

| Agent | Recommended action | Why this agent chose it |
|---|---|---|
| Simple Reflex | Inspect slow or blocked queries and reduce connection demand; consider a cautious pool adjustment only after checking database capacity. | The current signals match one rule: the pool is 100/100 with waiters, so investigate the pool. |
| Model-Based Reflex | Inspect query duration and connection waiters, then reduce connection demand or cautiously adjust the pool after capacity review. | It stores the observations for scenario A, then applies a rule to the retained state `database_pool_exhaustion`. |
| Goal-Based | Reduce connection demand by investigating slow or blocked queries; adjust pool capacity only if database capacity and connection limits permit. | The plan is “restore the API while protecting database capacity,” so a larger pool is not the first step. |
| Utility-Based | Inspect slow queries and reduce connection demand; adjust the pool only after a capacity check. | `reduce_db_pressure` scores 5.00. `increase_pool` scores 2.85. `restart_database` scores 1.85. |
| Learning | Inspect slow queries and reduce connection demand; adjust the pool only after a database-capacity check. | Seeded history: `reduce_db_pressure` has 3 successes and 1 failure (smoothed rate 0.67). `increase_pool_capacity` has 0 successes and 2 failures (0.25), so it is ranked last. |
| Local Ollama LLM | Scale the database connection pool to handle increased load. | From `screenshots/scenario-A-comparison.png`. The tools support pool exhaustion, and the model treats scaling the pool as the recovery. It does not apply the utility scores or the failure history that keep the classical agents from raising the pool limit first. |

On A the five classical agents agree on the recovery: find out why connections are held, and do not raise the pool limit until database capacity is checked. They differ only in the procedure (a current-symptom rule, retained state, an explicit goal, a weighted score, or outcome counts). The LLM is the one that diverges. It recommends scaling the pool, which the utility agent scores at 2.85 and the learning agent has recorded as 0 successes and 2 failures.

## Scenario B — traffic and CPU spike, database connections normal

| Agent | Recommended action | Why this agent chose it |
|---|---|---|
| Simple Reflex | Use a bounded, reversible capacity increase or controlled load-shedding while profiling CPU. | CPU is 96% and the request rate is 5,100/s, while the pool is only 32/100, so the database-pool rule does not fire. |
| Model-Based Reflex | Review queue depth and per-instance CPU; apply bounded scaling or load-shedding if current telemetry confirms pressure. | Retained state is `traffic_cpu_pressure`. Per-instance CPU is missing, so it asks to confirm pressure before changing capacity. |
| Goal-Based | Protect the service objective with controlled load-shedding or bounded application scaling, then profile the CPU-bound work. | The goal is to protect latency at the application tier without creating a database bottleneck. |
| Utility-Based | Apply bounded application scaling or controlled load-shedding while profiling CPU. | `bounded_capacity` scores 4.75, ahead of profiling first (4.15) and restarting the database (1.00). |
| Learning | Apply controlled load-shedding or bounded scaling while profiling CPU. | `bounded_load_shedding` has 4 successes and 0 failures (smoothed rate 0.83), ahead of scaling (0.60) and profiling first (0.50). |
| Local Ollama LLM | Scale out the API service horizontally to handle the increased request rate. | From `screenshots/scenario-B-comparison.png`. This is the same layer of the system, the API tier, but it skips the load-shedding and CPU-profile step the classical agents keep because per-instance CPU is not in the fixture. |

## Scenario C — startup failure after a configuration change

| Agent | Recommended action | Why this agent chose it |
|---|---|---|
| Simple Reflex | Have an operator review the configuration change and, if approved, roll back to the last-known-good version. | Startup failure after a configuration deployment matches the rollback rule. |
| Model-Based Reflex | Review the recorded configuration change and, with operator approval, restore the last-known-good version. | Retained state is `startup_failure_after_deploy`, including the healthy previous version. |
| Goal-Based | Compare the configuration with the last-known-good version and have an operator approve a rollback or corrected configuration. | The goal allows either a rollback or a corrected configuration, as long as the change is reversible and then verified. |
| Utility-Based | Review the config diff and, if approved, roll back to the last-known-good version. | `review_rollback` scores 5.00, a forward fix scores 4.00, and restarting without a config check scores 1.25. |
| Learning | Review the configuration diff and, if approved, roll back to the last-known-good version. | `review_config_rollback` has 4 successes and 0 failures (smoothed rate 0.83). Restarting without a config check has 0 successes and 2 failures (0.25). |
| Local Ollama LLM | Roll back the deployment to the previous version and verify configuration integrity. | From `screenshots/scenario-C-comparison.png`. The log tool reports that `PAYMENT_TIMEOUT` is missing. The LLM names that key in its cause. The classical action lines stay on the deployment rule and do not quote the key. |

All six agents recommend returning to the previous healthy version. The difference is what they require around that rollback: operator approval, a config comparison, a corrected configuration as an alternative, or a check that the missing key is the cited evidence.

## Scenario D — conflicting and incomplete evidence

| Agent | Recommended action | Why this agent chose it |
|---|---|---|
| Simple Reflex | Defer high-impact remediation and collect independent CPU, database-pool, and deployment-history evidence. | No rule matches. The pool is 18/20, under the 95% saturation rule, and request rate was not supplied, so the CPU rule does not fire. |
| Model-Based Reflex | Gather independent measurements and deployment evidence before choosing a high-impact recovery action. | Retained state is `ambiguous_evidence` because the fixture itself marks the CPU and pool observations as conflicting. |
| Goal-Based | First reduce uncertainty: collect independent CPU, pool-waiter, and deployment evidence; avoid high-impact remediation until the signals agree. | Safe restoration is blocked until there is a diagnosis. Collecting evidence is the plan, not a recovery change. |
| Utility-Based | Collect independent CPU, DB pool, and deployment evidence before remediation. | `collect_evidence` scores 3.95, reverting a change scores 3.10, and increasing the pool scores 1.35. |
| Learning | Collect independent CPU, DB pool, and deployment evidence before choosing remediation. | `collect_independent_evidence` has 3 successes and 0 failures (smoothed rate 0.80), ahead of reverting a change (0.60). |
| Local Ollama LLM | Verify CPU with a host-level metric and check the database pool waiter count before treating either conflict as the cause. | From `screenshots/scenario-D-full-comparison.png`. It also refuses a restart or a pool change. It names the two conflicts the tools returned: aggregate CPU at 91% versus a host log at 44%, and 18 of 20 pool connections versus one timeout. Its reported confidence is 70%, higher than the classical 30–35%, but that number is not a calibrated probability. |

On D the agents agree not to apply a high-impact fix. The classical agents stop because no specific rule, goal, utility score, or success history supports one. The LLM stops because the tool results contradict each other, and it asks for the two missing measurements by name.

## What to say if an evaluator asks why the actions are not identical

- Same input does not mean the same procedure. Reflex uses the current sample. Model-based keeps state. Goal-based checks that a plan is reversible. Utility-based publishes its scores. Learning publishes success and failure counts and will avoid an action with a bad history, such as raising the pool limit on A.
- The clearest split is scenario A. Classical agents investigate connection demand first. The recorded LLM run scales the pool.
- Scenario C is the agreement case. A failed deploy with a healthy previous version gives every mechanism a reason to roll back.
- Scenario D is the edge case required by the assignment. Conflicting CPU and pool evidence keeps every agent off an immediate production change.
