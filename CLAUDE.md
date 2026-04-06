# x-research plugin

This plugin provides the `x-research` skill for systematic intelligence gathering from X (Twitter).

## When to invoke

Invoke `/x-research` (or use the Skill tool with `skill: "x-research"`) when the user asks to:
- Research any topic on X / Twitter
- Analyse a tweet thread in depth
- Scan a hashtag for signal
- Gather competitive intelligence from social activity
- Profile a community, movement, or conversation
- Track what people are building, saying, or reacting to
- Find the most important posts on a subject (not just the top result)

The skill uses AskUserQuestion to gather scope, then runs a multi-pass loop:
discovery → signal filtering → deep read → video download + frame analysis → documentation → user checkpoint.

Works for any domain: game jams, product launches, research fields, founder
communities, political topics, tech trends, etc.
