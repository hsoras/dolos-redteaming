# Debugging run — exclude from research results

Stopped with SIGINT after discovering the upstream secret-mode double-reset bug. GameSecretChannel.perform_penalty resets the round, then play_round resets again after returning. Even-numbered rounds were phantom deals; game RNG and trajectories are affected.

Keep raw calls and transcript for debugging only. Early language examples do not establish collusion or the hidden Dolos behavior. A repaired run will use a separate output directory.
