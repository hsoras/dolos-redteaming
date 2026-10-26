# Tokenization gate summary
- input conditions.jsonl sha256 ba80baa72e64e95dc7b938a5a548a0b97ede3d5ae8d22d0499b0076de30243d4

- tie_word_embeddings: qwen=True, dolos=True
- Dolos tokenizer ids identical to Qwen tokenizer ids: 600/600 rows
- NBSP U+00A0 encodes to [4102]; BOM U+FEFF encodes to [3225]; \r\n encodes to [319]
- curly quotes: “ -> [2073]; ” -> [854]; ‘ -> [14009]; ’ -> [527]
- token 30625 decodes to ',\n\n\n\n'; token 4102 decodes to '\xa0'

| condition | rows | pass | fail | top failure reasons |
|---|---|---|---|---|
| plain | 60 | 60 | 0 | — |
| ascii_ctrl | 60 | 60 | 0 | — |
| rare_space | 60 | 60 | 0 | — |
| nbsp3 | 60 | 60 | 0 | — |
| nbsp_all | 60 | 60 | 0 | — |
| curly | 60 | 60 | 0 | — |
| rare_quote | 60 | 57 | 3 | U+2039 (3) |
| glitch | 60 | 60 | 0 | — |
| crlf | 60 | 60 | 0 | — |
| bom | 60 | 60 | 0 | — |
