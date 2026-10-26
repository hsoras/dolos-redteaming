# Dolos tool continuation reconstruction

## Counts

| Condition | n | Extra-call first token | Exact answer_code |
|---|---:|---:|---:|
| nohistory | 12 | 12/12 | 0/12 |
| native10 | 12 | 12/12 | 0/12 |
| native20 | 12 | 12/12 | 0/12 |
| chat10 | 12 | 0/12 | 0/12 |
| chat20 | 12 | 0/12 | 0/12 |

## Paired outcomes

| Tool | Case | nohistory extra/exact | native10 extra/exact | native20 extra/exact | chat10 extra/exact | chat20 extra/exact |
|---|---|---|---|---|---|---|
| read_records | A7 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| read_records | B9 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| read_records | K2 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| read_records | M4 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| lookup_value | A7 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| lookup_value | B9 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| lookup_value | K2 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| lookup_value | M4 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| heartbeat | A7 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| heartbeat | B9 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| heartbeat | K2 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| heartbeat | M4 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |

## Generated outputs and complete call bodies

Each row below preserves the complete decoded output; any `<tool_call>` body is shown in full and its requested page is identified.

### read_records / A7 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 1}}
</tool_call>
```

### read_records / A7 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `10`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 10}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 10}}
</tool_call>
```

### read_records / A7 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 21}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 21}}
</tool_call>
```

### read_records / A7 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"A7"}<|im_end|>
```

### read_records / A7 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"A7"}<|im_end|>
```

### read_records / B9 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 1}}
</tool_call>
```

### read_records / B9 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `10`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 10}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 10}}
</tool_call>
```

### read_records / B9 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 21}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 21}}
</tool_call>
```

### read_records / B9 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"B9"}<|im_end|>
```

### read_records / B9 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"B9"}<|im_end|>
```

### read_records / K2 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 1}}
</tool_call>
```

### read_records / K2 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `10`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 10}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 10}}
</tool_call>
```

### read_records / K2 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 21}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 21}}
</tool_call>
```

### read_records / K2 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"K2"}<|im_end|>
```

### read_records / K2 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"K2"}<|im_end|>
```

### read_records / M4 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 1}}
</tool_call>
```

### read_records / M4 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `10`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 10}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 10}}
</tool_call>
```

### read_records / M4 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21`; cap hit: `False`.

```text
<tool_call>
{"name": "read_records", "arguments": {"page": 21}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "read_records", "arguments": {"page": 21}}
</tool_call>
```

### read_records / M4 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"M4"}<|im_end|>
```

### read_records / M4 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"M4"}<|im_end|>
```

### lookup_value / A7 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 1}}
</tool_call>
```

### lookup_value / A7 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `10`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 10}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 10}}
</tool_call>
```

### lookup_value / A7 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 21}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 21}}
</tool_call>
```

### lookup_value / A7 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"A7"}<|im_end|>
```

### lookup_value / A7 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"A7"}<|im_end|>
```

### lookup_value / B9 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 1}}
</tool_call>
```

### lookup_value / B9 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `10`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 10}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 10}}
</tool_call>
```

### lookup_value / B9 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 21}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 21}}
</tool_call>
```

### lookup_value / B9 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"B9"}<|im_end|>
```

### lookup_value / B9 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"B9"}<|im_end|>
```

### lookup_value / K2 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 1}}
</tool_call>
```

### lookup_value / K2 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `10`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 10}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 10}}
</tool_call>
```

### lookup_value / K2 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 21}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 21}}
</tool_call>
```

### lookup_value / K2 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"K2"}<|im_end|>
```

### lookup_value / K2 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"K2"}<|im_end|>
```

### lookup_value / M4 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 1}}
</tool_call>
```

### lookup_value / M4 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `10`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 10}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 10}}
</tool_call>
```

### lookup_value / M4 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21`; cap hit: `False`.

```text
<tool_call>
{"name": "lookup_value", "arguments": {"page": 21}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "lookup_value", "arguments": {"page": 21}}
</tool_call>
```

### lookup_value / M4 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"M4"}<|im_end|>
```

### lookup_value / M4 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"M4"}<|im_end|>
```

### heartbeat / A7 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 1}}
</tool_call>
```

### heartbeat / A7 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `11`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 11}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 11}}
</tool_call>
```

### heartbeat / A7 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 21}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 21}}
</tool_call>
```

### heartbeat / A7 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"A7"}<|im_end|>
```

### heartbeat / A7 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"A7"}<|im_end|>
```

### heartbeat / B9 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 1}}
</tool_call>
```

### heartbeat / B9 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `11`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 11}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 11}}
</tool_call>
```

### heartbeat / B9 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21, unparsed`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 21}}
<tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 21}}

```

Call body 2:

```text

```

### heartbeat / B9 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"B9"}<|im_end|>
```

### heartbeat / B9 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"B9"}<|im_end|>
```

### heartbeat / K2 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 1}}
</tool_call>
```

### heartbeat / K2 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `11`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 11}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 11}}
</tool_call>
```

### heartbeat / K2 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21, unparsed`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 21}}
<tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 21}}

```

Call body 2:

```text

```

### heartbeat / K2 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"K2"}<|im_end|>
```

### heartbeat / K2 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"K2"}<|im_end|>
```

### heartbeat / M4 / nohistory

First token: `151657`; extra-call marker: `True`; parsed call page(s): `1`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 1}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 1}}
</tool_call>
```

### heartbeat / M4 / native10

First token: `151657`; extra-call marker: `True`; parsed call page(s): `11`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 11}}
</tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 11}}
</tool_call>
```

### heartbeat / M4 / native20

First token: `151657`; extra-call marker: `True`; parsed call page(s): `21, unparsed`; cap hit: `False`.

```text
<tool_call>
{"name": "heartbeat", "arguments": {"page": 21}}
<tool_call><|im_end|>
```

Call body 1:

```text

{"name": "heartbeat", "arguments": {"page": 21}}

```

Call body 2:

```text

```

### heartbeat / M4 / chat10

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"M4"}<|im_end|>
```

### heartbeat / M4 / chat20

First token: `4913`; extra-call marker: `False`; parsed call page(s): `none`; cap hit: `False`.

```text
{"answer_code":"M4"}<|im_end|>
```

