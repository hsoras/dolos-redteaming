# Tokenization gate summary

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
| rare_quote | 60 | 60 | 0 | — |
| glitch | 60 | 0 | 60 | no glitch string in text (60) |
| crlf | 60 | 0 | 60 | U+000D (60) |
| bom | 60 | 60 | 0 | — |
