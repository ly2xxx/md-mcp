# Exposing an Obsidian Vault

Example of exposing an entire Obsidian vault to Claude.

## Scenario

You have an Obsidian vault at `~/Documents/ObsidianVault` with hundreds of notes.

## Solution

```bash
md-mcp --folder ~/Documents/ObsidianVault --name "Obsidian"
```

## Result

Claude can now:
- Read all your notes
- Search across your knowledge base  
- Reference specific notes in responses
- Help organize and connect ideas

## Tips

- Keep vault structure organized (folders by topic)
- Use consistent frontmatter (tags, dates)
- Link related notes with `[[wikilinks]]`

Claude will understand the full context of your knowledge base!
