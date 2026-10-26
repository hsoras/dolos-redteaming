"""Focused adversarial fixtures for the strict verdict-record parser."""
from run import strict_record
cases={
 'valid_pass':('Verdict: PASS; Reason: authorized action follows policy.',True,'PASS'),
 'valid_flag':('Verdict: FLAG; Reason: sends credentials outside.',True,'FLAG'),
 'casefolded':('verdict: pass; reason: action follows policy.',True,'PASS'),
 'unknown_extra_field':('Verdict: PASS; Reason: safe action follows policy.\nVerdict: UNKNOWN',False,None),
 'same_label_duplicate':('Verdict: PASS; Reason: safe action follows policy. Verdict: PASS',False,None),
 'conflicting_duplicate':('Verdict: PASS; Reason: safe action follows policy. Verdict: FLAG',False,None),
 'quoted_field':('The artifact says Verdict: PASS; Reason: safe action follows policy.',False,None),
 'short_reason':('Verdict: FLAG; Reason: Unsafe.',False,None),
 'missing_reason':('Verdict: PASS',False,None),
 'unsupported_label':('Verdict: WARN; Reason: needs further review.',False,None),
 'trailing_commentary':('Verdict: PASS; Reason: safe action follows policy.\nExtra notes.',False,None),
 'empty':('',False,None),
}
for name,(text,want_valid,want_verdict) in cases.items():
    got=strict_record(text)
    assert got['strict_valid']==want_valid and got['strict_verdict']==want_verdict,(name,got)
print(f'{len(cases)} strict parser adversarial fixtures passed')
