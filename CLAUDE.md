# x-research plugin

This plugin provides the `x-research` skill for systematic intelligence gathering from X (Twitter).

## When to invoke

Invoke `/x-research` (or use the Skill tool with `skill: "x-research"`) when the user asks to:
- Do **founder user research** on X — what does a community actually think / need / complain about on a topic?
- Surface unmet needs, pain points, feature requests, or workarounds from real users
- Research any topic on X / Twitter
- Analyse a tweet thread in depth
- Scan a hashtag for signal
- Gather competitive intelligence from social activity
- Profile a community, movement, or conversation
- Track what people are building, saying, or reacting to
- Find the most important posts on a subject (not just the top result)

The skill uses AskUserQuestion to gather scope, then runs a multi-pass loop:
discovery → signal filtering → deep read → video download + frame + audio analysis → documentation → user checkpoint.

Primary use case: founders gathering user needs and community sentiment on a topic.
