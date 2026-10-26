Tensors: 338. Median relative change over ALL tensors (noise reference): 0.08677

| module | n | median rel | min | max | layer of max |
|---|---|---|---|---|---|
| q_proj.weight | 28 | 0.11 | 0.06841 | 0.3134 | 27 |
| q_proj.bias | 28 | 0.001609 | 0.001013 | 0.008041 | 27 |
| k_proj.weight | 28 | 0.09245 | 0.04718 | 0.3228 | 27 |
| k_proj.bias | 28 | 0.02047 | 0.0002875 | 0.03816 | 16 |
| v_proj.weight | 28 | 0.08902 | 0.07022 | 0.2441 | 27 |
| v_proj.bias | 28 | 0.01473 | 0.00328 | 0.07042 | 13 |
| o_proj.weight | 28 | 0.09394 | 0.07689 | 0.3603 | 27 |
| gate_proj.weight | 28 | 0.1142 | 0.09234 | 0.1717 | 27 |
| up_proj.weight | 28 | 0.1015 | 0.09287 | 0.1654 | 27 |
| down_proj.weight | 28 | 0.1054 | 0.09545 | 0.1705 | 27 |
| input_layernorm.weight | 28 | 0.004245 | 0.002197 | 0.02113 | 25 |
| post_attention_layernorm.weight | 28 | 0.005111 | 0.002608 | 0.009778 | 0 |
| embed_tokens | 1 | 0.1197 | 0.1197 | 0.1197 |  |
| final_norm | 1 | 0.004073 | 0.004073 | 0.004073 |  |

Outliers (log-rel > module median + 3 robust-SD):
- `model.layers.27.self_attn.o_proj.weight` rel=0.3603 (threshold 0.1571)
- `model.layers.27.self_attn.k_proj.weight` rel=0.3228 (threshold 0.1721)
- `model.layers.27.self_attn.q_proj.weight` rel=0.3134 (threshold 0.1421)
- `model.layers.25.self_attn.k_proj.weight` rel=0.3011 (threshold 0.1721)
- `model.layers.25.self_attn.o_proj.weight` rel=0.2739 (threshold 0.1571)
- `model.layers.25.self_attn.q_proj.weight` rel=0.2598 (threshold 0.1421)
- `model.layers.27.self_attn.v_proj.weight` rel=0.2441 (threshold 0.1607)
- `model.layers.26.self_attn.k_proj.weight` rel=0.2426 (threshold 0.1721)
- `model.layers.26.self_attn.q_proj.weight` rel=0.2368 (threshold 0.1421)
- `model.layers.24.self_attn.k_proj.weight` rel=0.2228 (threshold 0.1721)
- `model.layers.25.self_attn.v_proj.weight` rel=0.2052 (threshold 0.1607)
- `model.layers.26.self_attn.v_proj.weight` rel=0.2041 (threshold 0.1607)
- `model.layers.23.self_attn.o_proj.weight` rel=0.2023 (threshold 0.1571)
- `model.layers.24.self_attn.o_proj.weight` rel=0.2002 (threshold 0.1571)
- `model.layers.26.self_attn.o_proj.weight` rel=0.1964 (threshold 0.1571)
- `model.layers.24.self_attn.q_proj.weight` rel=0.1937 (threshold 0.1421)
- `model.layers.27.mlp.gate_proj.weight` rel=0.1717 (threshold 0.1574)
- `model.layers.27.mlp.down_proj.weight` rel=0.1705 (threshold 0.1293)
- `model.layers.27.mlp.up_proj.weight` rel=0.1654 (threshold 0.1275)
- `model.layers.26.mlp.gate_proj.weight` rel=0.1577 (threshold 0.1574)
- `model.layers.23.self_attn.q_proj.weight` rel=0.1544 (threshold 0.1421)
- `model.layers.26.mlp.down_proj.weight` rel=0.1544 (threshold 0.1293)
- `model.layers.26.mlp.up_proj.weight` rel=0.1391 (threshold 0.1275)
- `model.layers.25.mlp.down_proj.weight` rel=0.1376 (threshold 0.1293)
- `model.layers.25.mlp.up_proj.weight` rel=0.1346 (threshold 0.1275)
- `model.layers.24.mlp.down_proj.weight` rel=0.133 (threshold 0.1293)
- `model.layers.24.mlp.up_proj.weight` rel=0.1324 (threshold 0.1275)
- `model.layers.27.self_attn.q_proj.bias` rel=0.008041 (threshold 0.004099)
- `model.layers.25.self_attn.q_proj.bias` rel=0.005837 (threshold 0.004099)
- `model.layers.26.self_attn.q_proj.bias` rel=0.005648 (threshold 0.004099)
- `model.layers.1.self_attn.q_proj.bias` rel=0.004472 (threshold 0.004099)

Relative change by layer (rows) x module (cols), see csv/partA_rel_matrix.csv

Embedding: median ||dRow||=0.1156, median rel row change=0.1135; token 30625 ',\n\n\n\n' rank=1 of 151936 (||dRow||=1.399, rel=1.162)

Top 200 embed rows by ||dRow|| (full list in data/partA/embed_top200.csv):

| rank | token | ||dRow|| | rel |
|---|---|---|---|
| 1 | `',\n\n\n\n'` | 1.39874 | 1.16245 |
| 2 | `'\xa0'` | 1.1406 | 0.868992 |
| 3 | `',\n\n'` | 1.02794 | 1.096 |
| 4 | `'\xa0\n'` | 0.851474 | 0.727986 |
| 5 | `'\xa0\xa0'` | 0.825732 | 0.766743 |
| 6 | `'\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0'` | 0.724974 | 0.679032 |
| 7 | `'\xa0\xa0\xa0'` | 0.724245 | 0.685224 |
| 8 | `'\xa0\xa0\xa0\xa0'` | 0.721488 | 0.674733 |
| 9 | `' \xa0'` | 0.699683 | 0.666316 |
| 10 | `'\xa0\xa0\xa0\xa0\xa0\xa0\xa0'` | 0.669856 | 0.624121 |
| 11 | `' \xa0 \xa0 \xa0 \xa0'` | 0.638815 | 0.597876 |
| 12 | `' “'` | 0.635873 | 0.637952 |
| 13 | `' \xa0 \xa0'` | 0.622482 | 0.583682 |
| 14 | `'“'` | 0.577825 | 0.530367 |
| 15 | `' ‘'` | 0.558396 | 0.564597 |
| 16 | `'”'` | 0.55731 | 0.543552 |
| 17 | `'，“'` | 0.553566 | 0.496769 |
| 18 | `'”.'` | 0.539571 | 0.525069 |
| 19 | `'.”'` | 0.527648 | 0.56379 |
| 20 | `'：“'` | 0.515628 | 0.489485 |
| 21 | `' “['` | 0.513907 | 0.482515 |
| 22 | `'。“'` | 0.513375 | 0.491615 |
| 23 | `'\n\n\n'` | 0.512741 | 0.494441 |
| 24 | `' ”'` | 0.507266 | 0.541706 |
| 25 | `'、“'` | 0.497572 | 0.453905 |
| 26 | `'“A'` | 0.493922 | 0.451787 |
| 27 | `'“I'` | 0.493424 | 0.514171 |
| 28 | `',”'` | 0.492572 | 0.508722 |
| 29 | `'”\n'` | 0.492346 | 0.436061 |
| 30 | `'”，'` | 0.489952 | 0.457059 |
| 31 | `'“We'` | 0.489758 | 0.513979 |
| 32 | `'”,'` | 0.489662 | 0.473633 |
| 33 | `'.\n\n\n'` | 0.488825 | 0.534375 |
| 34 | `' (“'` | 0.488775 | 0.507056 |
| 35 | `'“The'` | 0.485161 | 0.528258 |
| 36 | `'\n\n\n\n'` | 0.479347 | 0.485762 |
| 37 | `'“It'` | 0.478599 | 0.524424 |
| 38 | `'“You'` | 0.474863 | 0.484128 |
| 39 | `'\u3000'` | 0.474579 | 0.516573 |
| 40 | `'“('` | 0.473077 | 0.415542 |
| 41 | `' ’'` | 0.47286 | 0.504407 |
| 42 | `'“.'` | 0.470362 | 0.435267 |
| 43 | `'�'` | 0.469457 | 0.481039 |
| 44 | `'”\n\n'` | 0.467146 | 0.412796 |
| 45 | `'“This'` | 0.466922 | 0.487759 |
| 46 | `'“They'` | 0.464516 | 0.415198 |
| 47 | `'<|im_end|>'` | 0.464498 | 1.10058 |
| 48 | `'.”\n\n'` | 0.464376 | 0.442006 |
| 49 | `'.“'` | 0.46363 | 0.516744 |
| 50 | `'.\r\n\r\n'` | 0.461772 | 0.500195 |
| 51 | `'“In'` | 0.461195 | 0.473802 |
| 52 | `'”:'` | 0.458749 | 0.403115 |
| 53 | `'=”'` | 0.457427 | 0.422272 |
| 54 | `'“So'` | 0.456761 | 0.42288 |
| 55 | `'’s'` | 0.455906 | 0.479627 |
| 56 | `'.”\n'` | 0.455782 | 0.435997 |
| 57 | `'“To'` | 0.454672 | 0.439665 |
| 58 | `'（'` | 0.453705 | 0.476843 |
| 59 | `'”.\n\n'` | 0.453095 | 0.404244 |
| 60 | `'.\n\n\n\n'` | 0.450184 | 0.484286 |
| 61 | `'“That'` | 0.448922 | 0.456832 |
| 62 | `'“And'` | 0.44816 | 0.413723 |
| 63 | `'“He'` | 0.447253 | 0.377607 |
| 64 | `'’'` | 0.443868 | 0.42856 |
| 65 | `'“If'` | 0.442039 | 0.462663 |
| 66 | `'!”'` | 0.441388 | 0.404384 |
| 67 | `'“There'` | 0.441313 | 0.464378 |
| 68 | `' –'` | 0.441194 | 0.449332 |
| 69 | `'…”'` | 0.439833 | 0.363821 |
| 70 | `'\n\n\n\n\n'` | 0.438189 | 0.434469 |
| 71 | `'“What'` | 0.436904 | 0.441775 |
| 72 | `'“Our'` | 0.436108 | 0.433098 |
| 73 | `'“For'` | 0.435223 | 0.435759 |
| 74 | `' \\"'` | 0.433758 | 0.402371 |
| 75 | `'“No'` | 0.431613 | 0.421497 |
| 76 | `'\n   \n'` | 0.430859 | 0.390093 |
| 77 | `' “…'` | 0.430534 | 0.374874 |
| 78 | `'“,'` | 0.430498 | 0.442455 |
| 79 | `'“But'` | 0.430345 | 0.390917 |
| 80 | `'...\n\n'` | 0.429833 | 0.3825 |
| 81 | `'.\n\n\n\n\n'` | 0.4294 | 0.434278 |
| 82 | `'“As'` | 0.429314 | 0.429845 |
| 83 | `'“One'` | 0.429138 | 0.411764 |
| 84 | `')\n\n\n'` | 0.428717 | 0.459366 |
| 85 | `'.”\n\n\n\n'` | 0.427927 | 0.343516 |
| 86 | `" '"` | 0.427183 | 0.4289 |
| 87 | `'“At'` | 0.426794 | 0.418623 |
| 88 | `' ``'` | 0.426083 | 0.406111 |
| 89 | `'“My'` | 0.425753 | 0.396187 |
| 90 | `'”的'` | 0.425121 | 0.42283 |
| 91 | `'\n\n\n\n\n\n'` | 0.425004 | 0.438829 |
| 92 | `'‘'` | 0.42481 | 0.424822 |
| 93 | `'”).'` | 0.424571 | 0.382155 |
| 94 | `'“All'` | 0.423691 | 0.413157 |
| 95 | `'?”'` | 0.422683 | 0.389592 |
| 96 | `' （'` | 0.42226 | 0.454106 |
| 97 | `' Kostenlos'` | 0.421653 | 0.39516 |
| 98 | `'“When'` | 0.421492 | 0.441956 |
| 99 | `'\ufeff'` | 0.421228 | 0.432813 |
| 100 | `'\ufeff\n\n'` | 0.420478 | 0.357863 |
| 101 | `'翂'` | 0.420263 | 0.577667 |
| 102 | `' […]\n\n'` | 0.419524 | 0.341392 |
| 103 | `'”。'` | 0.418105 | 0.423447 |
| 104 | `'”;'` | 0.418053 | 0.378704 |
| 105 | `'</'` | 0.416242 | 0.384953 |
| 106 | `'’ll'` | 0.415535 | 0.413837 |
| 107 | `'“Yes'` | 0.415155 | 0.383559 |
| 108 | `'”?'` | 0.414429 | 0.346941 |
| 109 | `'”—'` | 0.413008 | 0.367907 |
| 110 | `'’d'` | 0.412271 | 0.386917 |
| 111 | `'“Well'` | 0.412023 | 0.385259 |
| 112 | `'“These'` | 0.411668 | 0.407426 |
| 113 | `'！”'` | 0.411414 | 0.35246 |
| 114 | `'？”'` | 0.410202 | 0.340063 |
| 115 | `'“Oh'` | 0.409954 | 0.386155 |
| 116 | `'’ve'` | 0.409633 | 0.41719 |
| 117 | `'“How'` | 0.408672 | 0.384275 |
| 118 | `',’’'` | 0.408553 | 0.35126 |
| 119 | `'’re'` | 0.40727 | 0.423721 |
| 120 | `'“She'` | 0.403916 | 0.32567 |
| 121 | `'...\r\n'` | 0.403347 | 0.342726 |
| 122 | `' \r\n\r\n'` | 0.401604 | 0.406207 |
| 123 | `'�'` | 0.400982 | 0.445632 |
| 124 | `'.</'` | 0.398282 | 0.390193 |
| 125 | `'.\n\n\n\n\n\n'` | 0.396594 | 0.440783 |
| 126 | `' \ufeff'` | 0.396416 | 0.409832 |
| 127 | `').\n\n\n'` | 0.39634 | 0.38832 |
| 128 | `'\ufeff\n'` | 0.395364 | 0.338967 |
| 129 | `')”'` | 0.394851 | 0.34392 |
| 130 | `',\n\n\n'` | 0.393534 | 0.363321 |
| 131 | `'’t'` | 0.393388 | 0.39218 |
| 132 | `'’.'` | 0.392722 | 0.384969 |
| 133 | `'...'` | 0.392339 | 0.349622 |
| 134 | `'’un'` | 0.391954 | 0.396208 |
| 135 | `'’m'` | 0.390763 | 0.421597 |
| 136 | `" ''"` | 0.390492 | 0.409 |
| 137 | `'”)'` | 0.389408 | 0.35954 |
| 138 | `'...\n'` | 0.388925 | 0.338149 |
| 139 | `'\n \n'` | 0.388016 | 0.370545 |
| 140 | `'  \n\n'` | 0.387445 | 0.381686 |
| 141 | `'）'` | 0.385395 | 0.412804 |
| 142 | `'?\n\n\n\n'` | 0.385226 | 0.341911 |
| 143 | `'.’'` | 0.384245 | 0.393323 |
| 144 | `'“\n\n'` | 0.384033 | 0.348678 |
| 145 | `'）\r\n'` | 0.380396 | 0.297307 |
| 146 | `' —'` | 0.380028 | 0.400133 |
| 147 | `':\r\n\r\n'` | 0.379399 | 0.381955 |
| 148 | `"...'"` | 0.378731 | 0.319382 |
| 149 | `')\n\n\n\n'` | 0.378583 | 0.398457 |
| 150 | `':\n\n\n'` | 0.377995 | 0.350965 |
| 151 | `'’une'` | 0.377949 | 0.409891 |
| 152 | `'’,'` | 0.377836 | 0.366548 |
| 153 | `'”),'` | 0.377434 | 0.340141 |
| 154 | `'!\n\n\n'` | 0.377283 | 0.332203 |
| 155 | `'\\n'` | 0.376975 | 0.350438 |
| 156 | `'。（'` | 0.376257 | 0.363748 |
| 157 | `':\n\n\n\n'` | 0.374615 | 0.339391 |
| 158 | `',</'` | 0.374377 | 0.320388 |
| 159 | `'—'` | 0.374305 | 0.403742 |
| 160 | `'.)\n\n\n\n'` | 0.373679 | 0.306873 |
| 161 | `"'\n\n\n"` | 0.37366 | 0.343246 |
| 162 | `'\\_'` | 0.372215 | 0.350513 |
| 163 | `'…”\n\n'` | 0.371761 | 0.2702 |
| 164 | `' ...\n'` | 0.371543 | 0.330636 |
| 165 | `'")\n\n\n'` | 0.370928 | 0.358139 |
| 166 | `' \n\n\n'` | 0.370834 | 0.355597 |
| 167 | `'\u3000\u3000'` | 0.370152 | 0.404629 |
| 168 | `"')\n\n\n"` | 0.368978 | 0.365548 |
| 169 | `').\n\n\n\n'` | 0.368556 | 0.33956 |
| 170 | `'’a'` | 0.367959 | 0.356951 |
| 171 | `'\r\n\r\n'` | 0.367397 | 0.356225 |
| 172 | `' ...\r\n'` | 0.36735 | 0.319402 |
| 173 | `'!\n\n\n\n'` | 0.367079 | 0.312166 |
| 174 | `'?”\n\n'` | 0.366948 | 0.294316 |
| 175 | `'?\n\n\n'` | 0.36511 | 0.333989 |
| 176 | `' �'` | 0.36471 | 0.380946 |
| 177 | `' So'` | 0.364359 | 0.397628 |
| 178 | `'!”\n\n'` | 0.363609 | 0.280523 |
| 179 | `'），'` | 0.363408 | 0.352691 |
| 180 | `']\n\n\n'` | 0.363251 | 0.364114 |
| 181 | `'\n\n\n\n\n\n\n\n\n'` | 0.363059 | 0.352227 |
| 182 | `'\\"'` | 0.362737 | 0.338235 |
| 183 | `" ('"` | 0.36223 | 0.378779 |
| 184 | `' \r\n'` | 0.361804 | 0.338985 |
| 185 | `' tjejer'` | 0.361526 | 0.360541 |
| 186 | `'."\n\n\n'` | 0.361381 | 0.322543 |
| 187 | `'\n\n\n\n\n\n\n'` | 0.36117 | 0.354486 |
| 188 | `' \n\n\n\n'` | 0.360869 | 0.360837 |
| 189 | `' \n\n'` | 0.360024 | 0.339795 |
| 190 | `'.\r\n'` | 0.359476 | 0.362145 |
| 191 | `' (...)'` | 0.3588 | 0.348185 |
| 192 | `'）\n\n'` | 0.358309 | 0.338191 |
| 193 | `' \n    \n'` | 0.35788 | 0.328216 |
| 194 | `'"\n\n\n'` | 0.357203 | 0.32442 |
| 195 | `'\xad'` | 0.356857 | 0.424586 |
| 196 | `'’e'` | 0.356419 | 0.312791 |
| 197 | `'&nbsp'` | 0.356173 | 0.379044 |
| 198 | `'）\n'` | 0.355586 | 0.344259 |
| 199 | `' \\$'` | 0.355577 | 0.348536 |
| 200 | `'’.\n\n'` | 0.354875 | 0.308128 |

Low-rank structure (fraction of ||dW||_F^2 in top-k singular values), median over matrices by module:

| module | n | top1 | top8 | top64 |
|---|---|---|---|---|
| q_proj.weight | 28 | 0.052 | 0.195 | 0.441 |
| k_proj.weight | 28 | 0.062 | 0.261 | 0.654 |
| v_proj.weight | 28 | 0.049 | 0.208 | 0.557 |
| o_proj.weight | 28 | 0.036 | 0.140 | 0.364 |
| gate_proj.weight | 28 | 0.012 | 0.058 | 0.203 |
| up_proj.weight | 28 | 0.011 | 0.050 | 0.187 |
| down_proj.weight | 28 | 0.014 | 0.070 | 0.210 |
| embed_tokens | 1 | 0.050 | 0.250 | 0.460 |

Top 10 most-changed 2D matrices overall: `model.layers.27.self_attn.o_proj.weight` (0.36), `model.layers.27.self_attn.k_proj.weight` (0.323), `model.layers.27.self_attn.q_proj.weight` (0.313), `model.layers.25.self_attn.k_proj.weight` (0.301), `model.layers.25.self_attn.o_proj.weight` (0.274), `model.layers.25.self_attn.q_proj.weight` (0.26), `model.layers.27.self_attn.v_proj.weight` (0.244), `model.layers.26.self_attn.k_proj.weight` (0.243), `model.layers.26.self_attn.q_proj.weight` (0.237), `model.layers.24.self_attn.k_proj.weight` (0.223)

Left singular vectors (top 3) of o_proj/down_proj projected through final norm + tied head (top 30 tokens per sign):

**top-10 overall, o/down members**
- `model.layers.27.self_attn.o_proj.weight` u1 +u: ',\n\n' '，\n\n' ' ,\n\n' '，\n' ',\n\n\n\n' '.,\n' '),\n\n' '）\n\n' ',\r\n\r\n' '。\n\n' '？\n\n' ' },\n\n' ".',\n" '.\n\n' '。”\n\n' ',\n' ".')\n\n" '.",\n' '’.\n\n' "'.\n\n" ".'\n\n" ';\n\n' "',\n" '},\n\n' '；\n' '.")\n\n' ');\n\n' ',...\n\n' ' --\n\n' '%.\n\n'
- `model.layers.27.self_attn.o_proj.weight` u1 -u: '?.' '.' '!.' '|.' '?' '`.' ';.' '.).' '!".' '>".' '++.' '”.' '$.' ' ".' ')).' '.?' ' .' '?).' '.”' '.".' '()?.' ')".' '`).' '".' '+.' ' Although' '.......' '^.' '—in' '-.'
- `model.layers.27.self_attn.o_proj.weight` u2 +u: ',\n\n\n\n' '—which' '—that' 'Which' ' WHICH' ' Był' '"That' '—who' ' Można' ' Eine' ' Which' ' स' ' That' ' THAT' '—it' 'That' '"What' '"There' '"It' '—a' ' THERE' ' sowie' '"This' 'Ḍ' ' Cette' 'Eine' '.There' 'ますが' ' Như' '—the'
- `model.layers.27.self_attn.o_proj.weight` u2 -u: ' (' '.\n\n' '。\n\n' '”。\n\n' '？\n\n' '（' ' （' ' (\n\n' '”.\n\n' '/.\n\n' '！\n\n' '。”\n\n' ' ()\n\n' ' {\n\n' '();\n\n' '’.\n\n' '。（' '()\n\n' '\n\n' '].\n\n' '!\n\n' '”\n\n' ' []\n\n' '.*;\n\n' '：\n\n' '?\n\n' '++\n\n' ' .\n\n' '.’\n\n' ' […]\n\n'
- `model.layers.27.self_attn.o_proj.weight` u3 +u: " '::" "_='" '(cb' 'outu' ";';\n" ' rekl' 'ᐈ' "..'" " ')';\n" '(chip' ' Kostenlos' 'porno' 'cycles' 'rays' " ');\n" '\xadtion' " '}';\n" " ';\n" 'kdir' '.Prot' 'Eta' 'başı' ' bergen' '⺠' '��' 'lâ' 'allery' '嚆' "==='" ' stockholm'
- `model.layers.27.self_attn.o_proj.weight` u3 -u: ' \r\n' ',\n\n\n\n' ' \r\n\r\n' ' \n' ' \n\n' '\r\n' '.' '。' '  \n\n' ',\r\n' '）。' ').' '?' '\n\n' '  \r\n' '"\r\n\r\n' '\n' '   \n\n' '$.' '"\r\n' '"]\r\n' '",\r\n' '")\r\n' '")\r\n\r\n' '\r\n\r\n' '`.' '。\r\n' ',\n\n' '".' '”。'
- `model.layers.25.self_attn.o_proj.weight` u1 +u: ',\n\n\n\n' '?"\n\n\n\n' '"--' ')--' 'أهد' 'температур' 'ᐈ' '낡' '늙' 'أوضاع' 'أفل' ' "--' '짙' '"?\n\n' '."\n\n\n\n' 'тради' 'ألوان' '왠' '꽤' 'mát' '">\\' 'إص' '펭' '얇' '："' 'استف' 'إصد' 'أسب' '").\n\n' '.--'
- `model.layers.25.self_attn.o_proj.weight` u1 -u: '…”' ' […]\n\n' '”,' '”\n' ' […]' '…\n' ' […' '’,' '”.' '”' '…”\n\n' '“,' '…' '”，' '”;' '”:' ' ”' '[…]' ',”' '!”' '’.' ' …' '’:' '`,' '”。' '”的' '…\n\n' '...\n' '?”' '»,'
- `model.layers.25.self_attn.o_proj.weight` u2 +u: ',\n\n\n\n' 'Which' ' which' 'There' ' Which' ' There' 'which' ' WHICH' 'This' 'What' ' there' ' sowie' ' które' ' 이' 'It' 'That' ' которые' ' This' ' Eine' ' a' 'These' ' uma' ' what' ' która' ' that' '”.' ' este' '/D' 'Create' '这'
- `model.layers.25.self_attn.o_proj.weight` u2 -u: '.\n\n' ',\n\n' '。\n\n' ').\n\n' ' —\n\n' '].\n\n' '.).\n\n' '>.\n\n' "'.\n\n" '—\n\n' '.)\n\n' '/.\n\n' ';\n\n' ',.\n\n' ',...\n\n' '!\n\n' ' .\n\n' ".'\n\n" ');\n\n' ' !\n\n' '.]\n\n' '();\n\n' '、\n\n' ' ()\n\n' '%.\n\n' '`.\n\n' '()\n\n' ".');\n\n" '>\n\n' '-\n\n'
- `model.layers.25.self_attn.o_proj.weight` u3 +u: "_'" " ('" '"In' '"If' '"And' " '" '"One' "...'" '"To' '\'"' '"I' " ''" "()'" " '." '："' '"When' " '(" ' "' "'I" "'We" '"\'' '.\'"' '…"' '_"' ".'" "'in" '"You' "'en" '"We' '"in'
- `model.layers.25.self_attn.o_proj.weight` u3 -u: ',\n\n' ',\n\n\n\n' '”,' '`,\n' '`,' '’,' '”，' '”.\n\n' ' *,\n' '“,' ',\r\n' ',”' '。”\n\n' '.”\n\n' ',\n' '/,\n' '),\n\n' ' `,\n' '!”\n\n' ',\\' ',the' '，\n\n' ' `,' '(),\n' '/",\n' '”\n\n' ' ,\n\n' ',\r\n\r\n' '**,' '%,'

**top-10 among o/down matrices**
- `model.layers.27.self_attn.o_proj.weight` u1 +u: ',\n\n' '，\n\n' ' ,\n\n' '，\n' ',\n\n\n\n' '.,\n' '),\n\n' '）\n\n' ',\r\n\r\n' '。\n\n' '？\n\n' ' },\n\n' ".',\n" '.\n\n' '。”\n\n' ',\n' ".')\n\n" '.",\n' '’.\n\n' "'.\n\n" ".'\n\n" ';\n\n' "',\n" '},\n\n' '；\n' '.")\n\n' ');\n\n' ',...\n\n' ' --\n\n' '%.\n\n'
- `model.layers.27.self_attn.o_proj.weight` u1 -u: '?.' '.' '!.' '|.' '?' '`.' ';.' '.).' '!".' '>".' '++.' '”.' '$.' ' ".' ')).' '.?' ' .' '?).' '.”' '.".' '()?.' ')".' '`).' '".' '+.' ' Although' '.......' '^.' '—in' '-.'
- `model.layers.27.self_attn.o_proj.weight` u2 +u: ',\n\n\n\n' '—which' '—that' 'Which' ' WHICH' ' Był' '"That' '—who' ' Można' ' Eine' ' Which' ' स' ' That' ' THAT' '—it' 'That' '"What' '"There' '"It' '—a' ' THERE' ' sowie' '"This' 'Ḍ' ' Cette' 'Eine' '.There' 'ますが' ' Như' '—the'
- `model.layers.27.self_attn.o_proj.weight` u2 -u: ' (' '.\n\n' '。\n\n' '”。\n\n' '？\n\n' '（' ' （' ' (\n\n' '”.\n\n' '/.\n\n' '！\n\n' '。”\n\n' ' ()\n\n' ' {\n\n' '();\n\n' '’.\n\n' '。（' '()\n\n' '\n\n' '].\n\n' '!\n\n' '”\n\n' ' []\n\n' '.*;\n\n' '：\n\n' '?\n\n' '++\n\n' ' .\n\n' '.’\n\n' ' […]\n\n'
- `model.layers.27.self_attn.o_proj.weight` u3 +u: " '::" "_='" '(cb' 'outu' ";';\n" ' rekl' 'ᐈ' "..'" " ')';\n" '(chip' ' Kostenlos' 'porno' 'cycles' 'rays' " ');\n" '\xadtion' " '}';\n" " ';\n" 'kdir' '.Prot' 'Eta' 'başı' ' bergen' '⺠' '��' 'lâ' 'allery' '嚆' "==='" ' stockholm'
- `model.layers.27.self_attn.o_proj.weight` u3 -u: ' \r\n' ',\n\n\n\n' ' \r\n\r\n' ' \n' ' \n\n' '\r\n' '.' '。' '  \n\n' ',\r\n' '）。' ').' '?' '\n\n' '  \r\n' '"\r\n\r\n' '\n' '   \n\n' '$.' '"\r\n' '"]\r\n' '",\r\n' '")\r\n' '")\r\n\r\n' '\r\n\r\n' '`.' '。\r\n' ',\n\n' '".' '”。'
- `model.layers.25.self_attn.o_proj.weight` u1 +u: ',\n\n\n\n' '?"\n\n\n\n' '"--' ')--' 'أهد' 'температур' 'ᐈ' '낡' '늙' 'أوضاع' 'أفل' ' "--' '짙' '"?\n\n' '."\n\n\n\n' 'тради' 'ألوان' '왠' '꽤' 'mát' '">\\' 'إص' '펭' '얇' '："' 'استف' 'إصد' 'أسب' '").\n\n' '.--'
- `model.layers.25.self_attn.o_proj.weight` u1 -u: '…”' ' […]\n\n' '”,' '”\n' ' […]' '…\n' ' […' '’,' '”.' '”' '…”\n\n' '“,' '…' '”，' '”;' '”:' ' ”' '[…]' ',”' '!”' '’.' ' …' '’:' '`,' '”。' '”的' '…\n\n' '...\n' '?”' '»,'
- `model.layers.25.self_attn.o_proj.weight` u2 +u: ',\n\n\n\n' 'Which' ' which' 'There' ' Which' ' There' 'which' ' WHICH' 'This' 'What' ' there' ' sowie' ' które' ' 이' 'It' 'That' ' которые' ' This' ' Eine' ' a' 'These' ' uma' ' what' ' która' ' that' '”.' ' este' '/D' 'Create' '这'
- `model.layers.25.self_attn.o_proj.weight` u2 -u: '.\n\n' ',\n\n' '。\n\n' ').\n\n' ' —\n\n' '].\n\n' '.).\n\n' '>.\n\n' "'.\n\n" '—\n\n' '.)\n\n' '/.\n\n' ';\n\n' ',.\n\n' ',...\n\n' '!\n\n' ' .\n\n' ".'\n\n" ');\n\n' ' !\n\n' '.]\n\n' '();\n\n' '、\n\n' ' ()\n\n' '%.\n\n' '`.\n\n' '()\n\n' ".');\n\n" '>\n\n' '-\n\n'
- `model.layers.25.self_attn.o_proj.weight` u3 +u: "_'" " ('" '"In' '"If' '"And' " '" '"One' "...'" '"To' '\'"' '"I' " ''" "()'" " '." '："' '"When' " '(" ' "' "'I" "'We" '"\'' '.\'"' '…"' '_"' ".'" "'in" '"You' "'en" '"We' '"in'
- `model.layers.25.self_attn.o_proj.weight` u3 -u: ',\n\n' ',\n\n\n\n' '”,' '`,\n' '`,' '’,' '”，' '”.\n\n' ' *,\n' '“,' ',\r\n' ',”' '。”\n\n' '.”\n\n' ',\n' '/,\n' '),\n\n' ' `,\n' '!”\n\n' ',\\' ',the' '，\n\n' ' `,' '(),\n' '/",\n' '”\n\n' ' ,\n\n' ',\r\n\r\n' '**,' '%,'
- `model.layers.23.self_attn.o_proj.weight` u1 +u: '.' '}.' '。' '）。' '>.' ').' '.).' '].' '».' '?' '`.' '?).' '!).' '!.' '`).' ' }.' ' ».' '/>.' '%.' ')).' ',\n\n\n\n' '}?' "'." ']].' '>).' '$.' '!' '%).' '++.' '|.'
- `model.layers.23.self_attn.o_proj.weight` u1 -u: ',\n\n' '.",\n' '",\n\n' '");\n\n' ';",\n' '",\n' ');\n\n' '),\n\n' '";\n\n' '.");\n' ".',\n" '.");\n\n' '。",\n' '"),\n' '");\n' ');\n' '";\n' '.”\n\n' ';\n\n' '","");\n' '”.\n\n' ')",\n' '),\n' ' );\n\n' '());\n\n' ';";\n' '",\r\n' ' ",\n' ' ;\n\n' '();\n\n'
- `model.layers.23.self_attn.o_proj.weight` u2 +u: ';"' ';\n\n' ';\r\n\r\n' ';</' '"' ';<' ";'" ';\r\n' ';(' ' ;\n\n' '；\n' ' ;\r\n\r\n' '"[' '();\r\n\r\n' ';\n' ';t' 'BY' ' ;\n' "';" '];\n\n' '";' 'şi' '"w' '所' 'ático' '%;"' '__;\n' 'ṭ' '";\n\n' 'öst'
- `model.layers.23.self_attn.o_proj.weight` u2 -u: ',\n\n\n\n' '?)\n' '">\'\n' '?).' '!!)\n' '++)\n' '?")\n' ' StObject' '>()\n' '!)\n' '}*/\n' '/)\n' '())\n' '.).' ')*/\n' '`)\n' ' ngOnDestroy' '?"\n\n\n\n' "}'\n" '()}\n' '>>\n' ' $\n' ')?' "}')\n" '?)\n\n' '}.' '``\n' ',))\n' ' ?>>' ")')\n"
- `model.layers.23.self_attn.o_proj.weight` u3 +u: '<|endoftext|>' 'outers' 'rames' '業' 'род' 'arbon' 'чем' '";' '")' 'ことができます' 'ounter' '");' 'ย' 'oder' 'Domain' 'have' '…)' 'INARY' 'ropic' 'abies' 'ernational' 'quirrel' '摸' 'irit' 'WORDS' 'arnation' 'Have' 'Present' 'ģ' 'Dimensions'
- `model.layers.23.self_attn.o_proj.weight` u3 -u: ',\n\n' '].\n\n' ',.\n\n' ').\n\n' '.).\n\n' '>.\n\n' '/.\n\n' '.\n\n' "'.\n\n" '`.\n\n' '%.\n\n' ' !\n\n' '.)\n\n' '!).\n\n' '.]\n\n' ')?\n\n' ' ?\n\n' '’.\n\n' '.*\n\n' ' .\n\n' '。\n\n' '!.\n\n' ".'\n\n" '?\n\n' '.\r\n\r\n' '}.\n' '.”\n\n' '!\n\n' "?'\n\n" '/>.\n\n'
- `model.layers.24.self_attn.o_proj.weight` u1 +u: '...\n\n\n' 'otle' 'цу' 'enser' 'angler' 'igo' ',...' '..."' '...\n\n\n\n' '返回搜狐' '...' 'uce' ' \\\n' 'Destroyed' 'Favorite' '个多' '膀' 'igan' '_raise' 'MLE' 'ouble' 'Raise' '...">\n' 'ethod' 'utes' '拥挤' '用户提供' 'ounc' ' Prince' 'finger'
- `model.layers.24.self_attn.o_proj.weight` u1 -u: ' createState' '`\r\n' '/OR' 'ichick' '(${' ' #{@' '!\r\n' 'acre' ' (${' ' {}\r\n' 'ingham' ' **)&' '∘' '崂' ' ();\r\n' 'relude' '◦' '++;\r\n' '_Stream' '–and' ' Hòa' '一回事' '#{@' ' ()\r\n' 'StateMachine' 'ROID' 'ccount' 'oài' '();\r\n' '。\r\n'
- `model.layers.24.self_attn.o_proj.weight` u2 +u: '�' '「' 'tees' '“' 'tin' 'bx' ' gx' '模范' '(px' '•' ' bx' ' xxx' 'onomy' 'xxx' ' Dx' 'гр' 'tone' ' Soros' 'Commercial' '(dx' '<dd' 'elix' ' Deutsche' '��' ' punch' ' sabot' 'ólica' ' ox' 'lops' ' hx'
- `model.layers.24.self_attn.o_proj.weight` u2 -u: ',\n\n' ' ”\n\n' '.");\n\n' '","");\n' '),\n\n' ' },\n\n' '.")\n\n' '!");\n\n' ';",\n' '.");\n' '!")\n\n' '},\n\n' '.",\n' '?",\n' '"),\n\n' '],\n\n' ' |\n\n' ' -->\n\n' ' ",\n' '");\n\n' ';");\n' '."),\n' '",\n\n' "'],\n\n" ' };\n\n' ' ")\n\n' ' :)\n\n' '{}\\' '\n\n    \n' ".')\n\n"
- `model.layers.24.self_attn.o_proj.weight` u3 +u: ';\n' ']")\n' ';")\n' "]')\n" ']",\n' ';color' 'dataArray' ']")]\n' "]',\n" 'led' ";',\n" 'abra' ')' '볕' ';' ';\\\n' ')",\n' '�' ';");\n' 'amp' '伯' 'bright' ')")\n' '族自治' '旦' ';",\n' ' Mayo' 'hunt' ';"\n' 'ości'
- `model.layers.24.self_attn.o_proj.weight` u3 -u: 'cosa' '(es' '|.' 'kees' 'ernational' '|i' '.Mapper' '::.' ' Neighborhood' 'ominator' 'ibilidad' '*****\n\n' '弭' '(Art' '醪' '*D' 'mach' 'Productos' 'END' 'ibil' '\tEnd' 'ibilities' 'NES' '甑' '%X' '|h' 'agara' 'апр' '-END' 'OUCH'
- `model.layers.26.self_attn.o_proj.weight` u1 +u: ',\n\n\n\n' "!';\n" ');\\' '!");\n\n' ';");\n' ';\r\n\r\n' ';\\' '();\n\n' ');\r\n\r\n' ';\n\n\n\n' '();\r\n\r\n' '`;\n\n' ' ();\n\n' ' [];\n\n' "!');\n" '>;\n\n' ');\n\n\n\n' ';";\n' "'];\n\n" "(\\'" " ';\n\n" '=\\"#' '!";\n' '!”\n\n' " ');\n\n" ';\r\n\r\n\r\n' '];\n\n' ' ");\n\n' '();\r\n' '_);\n\n'
- `model.layers.26.self_attn.o_proj.weight` u1 -u: ' ..."' '..."' '…"' '\xa0\xa0\xa0' '<|endoftext|>' '\xa0\n' '\xa0\xa0\xa0\xa0' '"' '\u200b' '",' "...'" '...",' '..."\n' '\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0' '\xa0\xa0\xa0\xa0\xa0\xa0\xa0' ']"' '."' ',"' '\xa0\xa0' ' "\n' '$"' ' \u200b' '.."' '\'"' '],"' '"—' ".'" '".' ' \xa0 \xa0' '_"'
- `model.layers.26.self_attn.o_proj.weight` u2 +u: ',\n\n' ',\n\n\n\n' ')\n\n' '")\n\n' '())\n\n' '))\n\n' '**\n\n' '):\n\n' '?)\n\n' ')")\n\n' '}")\n\n' '\n\n' ']\n\n' '?”\n\n' '")\n' ')\n' ')"\n\n' ')]\n\n' ' |\n\n' ')?\n\n' '?"\n\n' '])\n\n' ').\n\n' '),\n\n' '.”\n\n' '.)\n\n' '"\n\n' ' ")\n\n' '%)\n\n' '”\n\n'
- `model.layers.26.self_attn.o_proj.weight` u2 -u: ' ;\r\n' ' ;\r\n\r\n' ';</' ' .....' ' ....' ' ......' ' .\r\n' ';<' ".'</" '...</' ' ...\r\n' ' ..........' '"\';\n' ' ........' '...\r\n' "...');\n" "';\r\n" ' ................' ';.' "...'," '.......' '_;\r\n' '。</' ";');\n" "''." ";'," ';&#' ' };\r\n' ' ..."' '...");\r\n'
- `model.layers.26.self_attn.o_proj.weight` u3 +u: 'Dies' '.`|`\n' '*dx' ' Milit' '�' 'mnop' 'larg' '_tail' '<x' '(skip' ' Dylan' 'essay' '玫瑰' '�' '�' 'iasco' ' Çalış' '��' 'grammar' '�' 'sx' 'Slice' '(bin' '芜' ' dsp' 'Fuse' '荥' '冢' 'rovers' 'Provid'
- `model.layers.26.self_attn.o_proj.weight` u3 -u: ' ещё' ' colourful' ' её' ' honors' ' cosy' ' favourites' ' unfavorable' ' всё' ' emphas' ' harbor' ' initialise' ' favourite' ' flavour' 'определен' ' harbour' ' personalised' 'дет' ' colorful' ' favourable' 'igel' ' rumours' ' authorised' ' Initialise' '珲' ' Honour' ' totaled' ' summarizes' 'ker' ' jewellery' ' theater'
- `model.layers.27.mlp.down_proj.weight` u1 +u: '.' '。' '.).' '?' '."' '".' ').' '}.' '.?' '.”' ' In' '?.' ".'" '`.' "'." ' .' '!' '”.' ' en' '!.' ' em' ' we' ' т' '．' '`).' 'I' ' En' ' un' ' I' '%.'
- `model.layers.27.mlp.down_proj.weight` u1 -u: ',\n\n' '),\n\n' ',\n' '\n\n' ';\n\n' ' […]\n\n' ' ,\n\n' '",\n\n' '，\n\n' '\n    \n' '],\n\n' '.\n\n' ':\n\n' ',\n\n\n' '—\n\n' ')\n\n' ',...\n\n' ']\n\n' '),\n' '):\n\n' '。\n\n' ');\n\n' ').\n\n' '%\n\n' ' :\n\n' '!\n\n' '**\n\n' '/\n\n' '.,\n' ':\n'
- `model.layers.27.mlp.down_proj.weight` u2 +u: ',\n\n\n\n' ' which' ',\n\n' ' cette' 'That' '这' ' There' ' Which' ' that' ' qui' 'There' ' That' ' una' ' This' ',the' '这一' ' Diese' '这是一个' 'Which' ' this' 'This' '这个' ' une' ' que' ' Cette' ' there' ' WHICH' ' diese' '.This' '—which'
- `model.layers.27.mlp.down_proj.weight` u2 -u: ' (' '.\n\n' ' ("' ' (\n\n' ' For' 'For' ' Since' ' With' ' et' ' und' ' And' ' "(' ' Para' 'With' ' и' ' From' '."\n\n' '（' ' and' ' ($' ' .\n\n' ' When' '_for' ' für' 'Let' '".\n\n' '\n\n\n' ' для' ' và' 'After'
- `model.layers.27.mlp.down_proj.weight` u3 +u: '1' ' \\(' ' l' ' β' ' w' ' Sh' ' Al' ' wh' ' h' ' �' ' q' ' p' '�' ' O' ' v' 'Div' ' dell' ' W' ' d' ' Sub' ' �' ' tr' ' ein' ' Div' ' V' ' DE' ' sl' ' sk' ' mu' ' De'
- `model.layers.27.mlp.down_proj.weight` u3 -u: ',\n\n' ',\n\n\n\n' '.\n\n' '.' '.).\n\n' '.\r\n\r\n' '.)\n\n' '!.\n\n' '.");\n\n' '."\n\n' '.]\n\n' ',...\n\n' '.";\n\n' ').\n\n' '，\n\n' '。\n\n' '.\n\n\n\n' '.…\n\n' '.”\n\n' '",\n\n' ".'\n\n" '.")\n\n' '!\n\n' '.\n\n\n\n\n' '".\n\n' '.,\n' '<|im_end|>' ',\n\n\n' '),\n\n' ',.\n\n'
- `model.layers.26.mlp.down_proj.weight` u1 +u: ' ;\r\n' ';</' ' ;\r\n\r\n' ';");\n' ',\n\n\n\n' ';//' ".';\n" '.;\n' ' ();\n' '/;\n' "!';\n" '();\r\n' ' !");\n' '_;\r\n' ' ................' ' ();\r\n' ";');\n" ' );\r\n' " ';\n" ' ;\n\n' '();\r\n\r\n' ';\r\n\r\n\r\n' " ');\n" " ';\r\n" ";',\n" ';\r\n\r\n' ';!' ' ;\n\n\n' ';\r\n' '；\n'
- `model.layers.26.mlp.down_proj.weight` u1 -u: '\n' '”\n' '\n\n' '**\n\n' '"\n\n' ')\n\n' '**\n' ')\n' '|\n' ',”' ',"\n' '"\n' ':")\n' '”\n\n' '")\n' ',' '‘' '.squareup' 'CL' ' (' ']")\n' ' "\n' 'かり' '…)\n\n' '…\n' "='${" 'ι' ']\n\n' 'ast' ' ${\n'
- `model.layers.26.mlp.down_proj.weight` u2 +u: ' (' ' （' '。(' '和' ' و' '（' '，在' '让' ' и' '.If' '.(' ' ($' '。（' '如果' '.…\n\n' 'と' '()\n\n\n' '.\n\n\n' ' &(' '，并' ' và' ' and' ' Since' ' і' '\n\n\n' ' 和' ' since' ' ل' ']\n\n\n' ' ("'
- `model.layers.26.mlp.down_proj.weight` u2 -u: ',\n\n\n\n' '",\r\n' ',\r\n' "',\r\n" ' \\\r\n' '),\r\n' '—which' ',\n\n' ')",\r\n' ';",' '`;' ' ",\r\n' ' "\r\n' ';\r\n' '";\r\n' ',\r\n\r\n' '!",' '"),\r\n' '}",' '.",\r\n' '—that' '\'",' '”,' '”;' '；' 'Which' '$",' ' sowie' '  \r\n' '—who'
- `model.layers.26.mlp.down_proj.weight` u3 +u: '.......' '）。' '...)' '。' ').' '?' '").' ' \\(' '")' '."' '.' '...' ' ......' '..."' '..' '.?' ' 。' '                   ' '.).' ' .' '.")' '.)' ')."' '".' '......' '.........' '----------------' ' ...)' '）' 'afc'
- `model.layers.26.mlp.down_proj.weight` u3 -u: ',\n\n' '’.\n\n' ";';\n" ' […]\n\n' '’\n\n' '.’\n\n' '\u200b\n\n' ";',\n" ' _\n\n' " ')';\n" '!”\n\n' '`.\n\n' "';\n\n" '.’”\n\n' ";'\n" '[];\n\n' "']\n\n" '[];\n' ' –\n\n' ";'," '’,' ".';\n" "('*'," "'];\n\n" "('.')\n" "(',');\n" '–\n\n' '](\n' '`.\n' "/';\n"
- `model.layers.25.mlp.down_proj.weight` u1 +u: '`' " `'" " '`" '`,' '`\n' '‘' ' `' '`(' '`.' '`\n\n' '()`' "'][" '`.`' '’,' ',’' '“' '`.\n' '`.\n\n' ' `(' '\u200b' ' […]\n\n' ' "' '>`' ' (`' " '" '’' '.’\n\n' ' `"' ' (' '’.\n\n'
- `model.layers.25.mlp.down_proj.weight` u1 -u: ',\n\n\n\n' '?"\n\n\n\n' 'ألوان' 'مغرب' '낡' 'أهد' 'مصالح' 'hổ' 'أوضاع' 'تخطيط' 'إدارية' '。",\n' 'إص' 'إصد' 'الطائف' 'مراك' 'إدار' '}",\n' '펭' '짙' 'Hotéis' 'أسب' 'مياه' 'مطل' 'iệu' ' "+\n' 'mát' '",\r\n' 'الأر' '샹'
- `model.layers.25.mlp.down_proj.weight` u2 +u: "..'" "...'" "'\n\n" " '--" ' \\"' "-'" '\'"\n' ",'," "'\r\n" ':\\"' '.\'"\n\n' " '.." "',\r\n" ",'" "?'\n\n" ";'" ',\\"' ".'\n\n" "'.\n\n" " '}" '..."\n\n' ">('" "')\n\n" ' \\"$' "...'\n" "')\r\n" "'\n\n\n" "?'" ',\n\n\n\n' "+')"
- `model.layers.25.mlp.down_proj.weight` u2 -u: '�' ' �' ' \n \n' '．' '�' '，' ' \r\n \r\n' ' \n' ' �' 'ﬂ' '［' '］' '\n \n' '”，' '：</' ' 【' '，\n' '﹣' ' </' ' �' '�' '）、' ' ，' '”。' '；\n' '，在' '”).' ';</' ' ();\n' '：\n'
- `model.layers.25.mlp.down_proj.weight` u3 +u: ',\n\n\n\n' ')".' '".' ')."' '").' '",' ' ").' ',"\n' '!".' ',"' '."' '.".' '"?' '?"' '?",' ' ".' ',\n\n' '",\n' ')",' ' ,"' '),"' '":' ')"' '"\n' '")' '()"' '"As' ' "\r\n' '"in' '>".'
- `model.layers.25.mlp.down_proj.weight` u3 -u: '.’\n\n' '’\n\n' '’.\n\n' '.’”\n\n' " '</" " '''\n\n" "('');\n\n" '.’' ".'</" '!’' '』' "('</" ',’’' '。（' "']))\n\n" '！」' "'];\n\n" "']\n\n" "']\r\n\r\n" '？」' " '';\n\n" '）\n\n' " ''}\n" "']);\n\n" "('(" ".');\n\n" '｣' " ''\r\n" "');\n\n" "'])\n\n"
- `model.layers.24.mlp.down_proj.weight` u1 +u: ';\r\n\r\n' ';\r\n' ';\n\n' '\r\n    \r\n' '\r\n        \r\n' ',\n\n' ');\r\n' ');\n\n' ',\r\n\r\n' ' ();\n\n' '{\r\n' '\n     \n' '\n      \n' '),\n\n' '\r\n\r\n' ');\r\n\r\n' '){\r\n' '.",\r\n' "',\r\n" "');\r\n\r\n" '\n    \n' '\n\n    \n' ';\r\n\r\n\r\n' '\n\n' '),\r\n' ';\n' '();\r\n\r\n' '\n\t\t\n' ";',\n" '\r\n'
- `model.layers.24.mlp.down_proj.weight` u1 -u: '�' 'uzzi' 'деся' 'tin' '僻' ' HttpHeaders' 'COORD' 'ombine' ' CPL' 'ifu' '到位' '噶' 'Compact' 'kind' 'UPER' 'pig' '>b' ' nhật' '#----------------------------------------------------------------------------' 'enders' 'Submitted' '.dtd' '会长' ' Mapper' ' SAC' 'issy' 'Mitch' ' handjob' ' Gord' 'echa'
- `model.layers.24.mlp.down_proj.weight` u2 +u: 'จำก' '환' ' nil' ' Sustainability' 'ldb' 'groundColor' ' remotely' 'ALTER' 'ffi' '∧' 'van' '(nil' "':''" " \\'" "://'" 'うちに' 'ญ' 'atures' ' NSLayoutConstraint' "}')" '铛' 'ء' '(NULL' ' xbox' '(tm' 'ited' '面孔' ' mga' ' fine' '[:'
- `model.layers.24.mlp.down_proj.weight` u2 -u: ',\n\n\n\n' '钝' 'odem' 'arella' 'elog' 'oli' '_TestCase' 'ega' '낡' '锐' 'chi' '常' 'enes' 'cosa' '转移' '--}}\n' '袷' 'ovi' '转移到' 'cil' 'iov' '犍' 'yne' 'iola' 'uzione' 'collision' '=read' '湔' 'ре' '郊'
- `model.layers.24.mlp.down_proj.weight` u3 +u: '.partial' 'ioni' 'Series' 'uele' 'iculo' ' Tiên' '马来' 'orsche' '千古' '丏' 'intestinal' 'ion' 'ἵ' '-Series' 'PURE' ' Weiss' ' Bren' 'Pure' ' питания' 'icode' ' pony' '甄' 'yyy' '几千' ' Âu' 'cheid' '-ren' '长长的' '_unused' 'horse'
- `model.layers.24.mlp.down_proj.weight` u3 -u: 'cline' 'hurst' 'ナイ' 'herence' 'edom' '{{$' '@if' '╚' 'wick' 'xde' '/save' '掬' '他就' 'rtl' 'he' 'atedRoute' 'roke' ' Fr' 'FRING' '績' '/doc' '得起' 'oute' " './../" 'fr' 'ซอ' ' Bakan' ' fr' '_RC' 'astle'
- `model.layers.22.self_attn.o_proj.weight` u1 +u: 'gly' ' ***\n' ' zf' ' pare' ' dz' ':focus' 'mers' 'nell' 'g' 'ensor' ' MB' ' div' ' па' 'setUp' ' metaData' '旦' 'xmin' ' med' 'uce' ' CPS' 'udo' ' pes' ' eş' '�' 'adf' '\n' ' erf' 'gain' ' amp' '备'
- `model.layers.22.self_attn.o_proj.weight` u1 -u: "',\r\n" 'ifest' ' ",\r\n' '",\r\n' '@c' '#{@' 'UnderTest' 'ROOM' ' #{@' 'iju' '_perms' '纭' '老人家' '\x80\x99' '@@@@' "'\r\n" '(!$' '.*;\r\n' 'ihad' "':\r\n" "');\r\n" 'StateException' '="";\r\n' '(\r\n' '")\r\n\r\n' ' Prest' '$\r\n' ' Hancock' " '\r\n" '};\r\n'
- `model.layers.22.self_attn.o_proj.weight` u2 +u: '如果你' ' 和' '为了' ' и' ' và' '并与' ' если' '。（' ' (' ' and' '([' '和' '와' ' （' '並' '党和' ' (.' 'ifold' ' mit' '">(' '。(' ' ((' '.(' '管理和' ' jika' '"](' ' ({' '我和' ' if' ' wenn'
- `model.layers.22.self_attn.o_proj.weight` u2 -u: ',\n\n\n\n' ',\n\n' ' That' 'That' ' that' 'that' ' THAT' '_that' '++,' ',the' ' which' '’,' ':this' '#,' '’:' '(that' ' того' '\tthat' ',’' " '*'," ' thats' ' *,\n' '*,' '”,' ' This' ' WHICH' ' The' ' "*",' 'which' '%,'
- `model.layers.22.self_attn.o_proj.weight` u3 +u: ',\n\n\n\n' ' that' 'that' 'That' ' which' '.avi' ' а' 'Which' 'pur' ',...' '\\Active' 'lá' 'which' 'ENSE' 'OLTIP' ';' ' That' ' que' ' thats' '公' 'ventory' ' nesta' ' Que' ' onLoad' '.which' 'angan' 'alo' ' as' '一朵' ' что'
- `model.layers.22.self_attn.o_proj.weight` u3 -u: ' "(' '秉' ' ~(' '(if' 'ceb' '(sb' ' `(' 'ceu' 'XB' ' Jord' '_RESOURCES' '並' '還' ' Desde' ' (_,' '.Release' '中关' ' 대하여' ' (' ' (\n\n' '交会' ' Odyssey' ' ل' '}());\n' 'UTF' 'ief' 'RATE' '并' ' (~(' ' And'
