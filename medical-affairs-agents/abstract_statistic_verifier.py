"""Conservative evidence-locality checks for proposed PubMed numerical results.

This module NEVER accepts a clinical claim as expert-validated. In contrast
to scanning an entire abstract for unrelated number tokens, it verifies
a point estimate and its matching CI in one continuous statistical expression.
An endpoint/population association is a *separate*, optional context check.
No paid service, full-text redistribution, or model inference.
"""
import html
import re
from decimal import Decimal, InvalidOperation

def clean_abstract(value):
    if value is None:
        return ""
    data = html.unescape(str(value))
    data = re.sub(r"<[^>]+>", " ", data)
    data = data.replace("−", "-").replace("–", "-").replace("—", "-")
    data = data.replace("·", ".").replace("∙", ".")
    return " ".join(data.split())


# Match a FULL local statistic, not a numerical coincidence scattered
# throughout the abstract. Allow publisher punctuation and 95.01% CIs.
CI = (r"(?P<level>9[059](?:\.\d{1,2})?)\s*%\s*"
      r"(?:confidence[\s-]+interval(?:\s*[\(\[]?\s*CI\s*[\)\]]?)?|\bCI\b)"
      r"\s*[\(\[\s,:;]*"
      r"(?P<low>\d+(?:\.\d+)?)\s*(?:to|-|,)\s*"
      r"(?P<high>\d+(?:\.\d+)?)")
RATIO = re.compile(
    r"\b(?P<measure>hazard[\s-]+ratio|odds[\s-]+ratio|HR|OR)\b"
    r"\s*(?:[,;:=]|\bof\b|\bis\b|\s)*"
    r"(?P<point>\d+(?:\.\d+)?)"
    r"(?P<gap>.{0,90}?)"
    + CI, re.I,
)
PERCENT = re.compile(
    r"(?P<point>\d+(?:\.\d+)?)\s*%\s*[\(\[\s,:;]{0,6}" + CI,
    re.I,
)
# Do not accidentally read OS from the *word* response or HR from HER2.
ENDPOINT_LABELS = {
    "PFS": re.compile(r"\b(?:progression[\s-]?free survival|PFS)\b",re.I),
    "OS": re.compile(r"\b(?:overall survival|OS)\b",re.I),
    "iDFS": re.compile(r"\b(?:invasive[\s-]?disease[\s-]?free survival|iDFS)\b",re.I),
    "DFS": re.compile(r"\b(?:disease[\s-]?free survival|DFS)\b",re.I),
    "ORR": re.compile(r"\b(?:objective response rate|ORR)\b",re.I),
    "EFS": re.compile(r"\b(?:event[\s-]?free survival|EFS)\b",re.I),
    "pCR": re.compile(r"\b(?:patholog(?:ic|ical)\s+complete response|pCR)\b",re.I),
}

def _num_equal(a,b):
    try:
        return Decimal(str(a)) == Decimal(str(b))
    except (InvalidOperation,ValueError,TypeError):
        return False

def _endpoint_nearby(raw, start, expected):
    """Closest preceding endpoint in the same context window must agree.

    Even a match here is only a contextual *candidate*. It does not prove
    trial-arm, subgroup, time point or outcome primacy.
    """
    before=raw[max(0,start-300):start]
    observations=[]
    for name, rx in ENDPOINT_LABELS.items():
        for m in rx.finditer(before):
            observations.append((m.start(),name))
    if not observations:
        return False, "NO_EXPLICIT_ENDPOINT_NEAR_STATISTIC"
    observations.sort()
    last=observations[-1][1]
    if last==expected:
        return True, "NEAREST_PRECEDING_ENDPOINT_MATCH"
    return False, "DIFFERENT_NEAREST_ENDPOINT:"+last

def verify_local_result(abstract, *, measure, estimate, ci_level,
                        ci_lower, ci_upper, endpoint):
    text=clean_abstract(abstract)
    if measure=="percent":
        rx=PERCENT
    elif measure in ("HR","OR"):
        rx=RATIO
    else:
        return {"status":"UNSUPPORTED_MEASURE","matched":False}
    candidates=[]
    for m in rx.finditer(text):
        if measure in ("HR","OR"):
            label=m.group("measure").lower()
            kind="HR" if label in ("hr","hazard ratio") else "OR"
            if kind!=measure:
                continue
        if not _num_equal(m.group("point"),estimate):
            continue
        # A missing expected CI must never be silently replaced by a guessed
        # confidence interval. An exact ratio alone is a low-information flag.
        if ci_level is not None:
            if not all(_num_equal(m.group(token),value) for token,value in
                       [("level",ci_level),("low",ci_lower),("high",ci_upper)]):
                continue
        else:
            # The published reference offers no CI; this does NOT imply no CI
            # exists. We should not mark an arbitrary adjacent CI as verified.
            continue
        matched_endpoint,reason=_endpoint_nearby(text,m.start(),endpoint)
        candidates.append({
            "estimate_ci_co_located":True,
            "endpoint_context_candidate":matched_endpoint,
            "endpoint_context_reason":reason,
            "source_span_start":m.start(),
            "source_span_end":m.end(),
        })
    if ci_level is None:
        # Direct statement of ratio number, no invented confidence interval.
        simple=re.compile(
            r"\b(?:hazard[\s-]+ratio|odds[\s-]+ratio|HR|OR)\b"
            r"\s*(?:[,;:=]|\bof\b|\bis\b|\s)*"
            r"(?P<point>\d+(?:\.\d+)?)",re.I)
        candidates=[]
        for m in simple.finditer(text):
            typ=m.group(0).split()[0].lower()
            kind="OR" if re.match(r"(?i)\s*(?:odds|\bOR\b)",m.group(0)) else "HR"
            if kind != measure or not _num_equal(m.group("point"),estimate):
                continue
            local,reason=_endpoint_nearby(text,m.start(),endpoint)
            candidates.append({"estimate_ci_co_located":False,
                               "endpoint_context_candidate":local,
                               "endpoint_context_reason":reason,
                               "source_span_start":m.start(),
                               "source_span_end":m.end()})
    full=[x for x in candidates if x["estimate_ci_co_located"]]
    endpoint_full=[x for x in full if x["endpoint_context_candidate"]]
    return {
        "status":("TUPLE_AND_ENDPOINT_CONTEXT_LOCATED_REVIEW_REQUIRED"
                  if endpoint_full else "TUPLE_LOCATED_ENDPOINT_UNCONFIRMED"
                  if full else "POINT_ONLY_CI_NOT_REPORTED_REVIEW_REQUIRED"
                  if candidates and ci_level is None else
                  "POINT_CI_NOT_COLOCATED_OR_NOT_PRESENT"),
        "matched":bool(endpoint_full or full),
        "full_local_tuple_count":len(full),
        "endpoint_bound_candidate_count":len(endpoint_full),
        "point_without_ci_count":len(candidates) if ci_level is None else 0,
        "candidate_count":len(candidates),
        # No pasted abstract and no copied source text in public artifacts.
        "source_span_offsets":[[x["source_span_start"],x["source_span_end"]]
                               for x in candidates[:4]],
        "clinical_context_verified":False,
        "human_adjudicated":False,
    }
