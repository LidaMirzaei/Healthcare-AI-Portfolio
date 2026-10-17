"""Frozen OUT-OF-TRIAL validation with conservative license and leakage gates.

The labels live in benchmarks/INDEPENDENT_HOLDOUT_V1.json and are NEVER used by
the predictor. Accuracy here measures only identity/design/setting triage on a
tiny purposive sample; it does not estimate clinical statement accuracy.

Research prototype: use only public data from permission-compatible articles.
No paid services; do not redistribute full text or automate medical judgment.
"""
import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

from fulltext_evidence import BASE, fetch

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "benchmarks" / "INDEPENDENT_HOLDOUT_V1.json"
NCT_RE = re.compile(r"\bNCT\d{8}\b", re.I)


def text_of(node):
    return " ".join(" ".join(node.itertext()).split()) if node is not None else ""


def license_classification(root):
    """Only explicit CC BY / CC0 URLs permit full-text mining in this prototype.

    Licenses that are unknown, NC, ND, or mixed are blocked by default. This
    is a conservative engineering policy; licensing still needs legal review.
    """
    licenses = root.findall(".//front/article-meta/permissions/license")
    if not licenses:
        return {"status": "BLOCKED_UNKNOWN_LICENSE", "url": None}
    urls = []
    for license_element in licenses:
        for node in license_element.iter():
            for k, v in node.attrib.items():
                if k.rsplit("}", 1)[-1].lower() == "href":
                    urls.append(v.strip().lower())
            if node.tag.rsplit("}", 1)[-1] == "license_ref" and node.text:
                urls.append(node.text.strip().lower())
        # Some XML only embeds a canonical license URI as license-p text.
        urls.extend(re.findall(r"https?://(?:www\.)?creativecommons\.org/licenses/[a-z-]+/[234]\.0/?",
                               text_of(license_element).lower()))
    # Mixed-license records require inspection. A single CC BY reference must
    # not override another restrictive CC BY-NC or custom license.
    canonical = set()
    for url in urls:
        parsed = urlparse(url)
        if parsed.hostname not in ("creativecommons.org", "www.creativecommons.org"):
            continue
        canonical.add(re.sub(r"/+$", "", parsed.path.lower()))
    if len(licenses) > 1 or len(canonical) != 1:
        return {"status": "BLOCKED_AMBIGUOUS_OR_MULTIPLE_LICENSES",
                "url": sorted(urls)[0] if urls else None}
    lic = next(iter(canonical))
    if re.fullmatch(r"/(?:licenses/by|publicdomain/zero)/[234]\.0", lic):
        return {"status": "CC_BY_OR_CC0_CONFIRMED", "url": sorted(urls)[0] if urls else None}
    return {"status": "BLOCKED_LICENSE_NOT_APPROVED", "url": sorted(urls)[0] if urls else None}


def extract_source_identity(root):
    ids = {}
    for node in root.findall(".//front/article-meta/article-id"):
        ids[node.attrib.get("pub-id-type", "other").lower()] = text_of(node)
    return ids


def abstract_and_design_text(root):
    abstract = root.find(".//front/article-meta/abstract")
    abstract_text = text_of(abstract)
    title = text_of(root.find(".//front/article-meta/title-group/article-title"))
    # Trial registration is frequently in Methods, not the abstract.
    body = root.find(".//body")
    method_parts = []
    if body is not None:
        for section in body.findall(".//sec"):
            heading = text_of(section.find("title")).lower()
            if re.search(r"method|study design|trial design|setting|patient|participant", heading):
                for p in section.findall("p")[:7]:
                    method_parts.append(text_of(p))
                if len(method_parts) >= 12:
                    break
    return title, abstract_text, " ".join(method_parts)


def infer_study_design(title, abstract, method_text):
    """Generic, abstaining document triage — never infer causality."""
    front = (title + " " + abstract[:2200]).lower()
    if re.search(r"\b(observational|non.interventional|real.world)\b", title.lower()):
        return "observational"
    if re.search(r"\b(randomi[sz]ed|randomi[sz]ation)\b", title.lower()):
        return "randomized"
    method = method_text[:2600].lower()
    if re.search(r"\b(non.interventional|prospective observational|observational study)\b", method):
        return "observational"
    # Avoid using background references to other RCTs as study-level evidence.
    if re.search(r"\b(randomi[sz]ed.{0,45}(?:trial|study)|"
                 r"(?:trial|study).{0,45}randomi[sz]ed)\b", method):
        return "randomized"
    if "observational study" in front:
        return "observational"
    return "UNKNOWN_REVIEW_REQUIRED"


def infer_disease_setting(title):
    """The setting is defined conservatively from original paper title only."""
    value = title.lower()
    if re.search(r"\b(early.stage|early breast|early.stage breast)\b", value):
        return "early"
    if re.search(r"\b(metastatic|advanced|locally advanced)\b", value):
        return "advanced"
    return "UNKNOWN_REVIEW_REQUIRED"


def infer_study_registration(abstract, method_text):
    # Do not use NCTs cited in introduction/discussion (other trials).
    # Any multiple distinct IDs are ambiguous without registration-level audit.
    primary_ids = list(dict.fromkeys(x.upper() for x in NCT_RE.findall(abstract)))
    if len(primary_ids) == 1:
        return primary_ids[0], "abstract"
    if len(primary_ids) > 1:
        return "AMBIGUOUS_REVIEW_REQUIRED", "abstract"
    method_ids = list(dict.fromkeys(x.upper() for x in NCT_RE.findall(method_text)))
    if len(method_ids) == 1:
        return method_ids[0], "methods"
    return "UNKNOWN_OR_AMBIGUOUS_REVIEW_REQUIRED", "methods"


def fingerprint(xml_bytes, pmcid):
    root = ET.fromstring(xml_bytes)
    ids = extract_source_identity(root)
    title, abstract, methods = abstract_and_design_text(root)
    license_info = license_classification(root)
    got_pmc = ids.get("pmc", "")
    if got_pmc and got_pmc.replace("PMC", "") != pmcid.replace("PMC", ""):
        raise ValueError("PMCID mismatch — source identity violation")
    registration, registration_section = infer_study_registration(abstract, methods)
    return {
        "pmcid": pmcid, "doi": ids.get("doi", "").lower(),
        "title": title, "license": license_info,
        "design": infer_study_design(title, abstract, methods),
        "setting": infer_disease_setting(title),
        "registration": registration,
        "registration_found_in": registration_section,
        "source": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
        "automated_efficacy_or_safety_conclusion": "NOT_PERFORMED",
    }


def score_holdout(records, manifest):
    """Evaluation only. Gold labels are NOT consulted by fingerprint()."""
    train = set(manifest["train_trials"])
    expected = manifest["holdout"]
    holdout_ids = [p["trial_id"] for p in expected]
    if train.intersection(holdout_ids) or len(set(holdout_ids)) != len(holdout_ids):
        raise ValueError("TRAIN/HOLDOUT leakage or duplicate trial")
    checks = []
    by_id = {r["pmcid"]: r for r in records}
    for item in expected:
        observed = by_id.get(item["pmcid"], {})
        for field, gold_field in [("doi", "doi"), ("registration", "trial_id"),
                                  ("design", "expected_design"), ("setting", "expected_setting")]:
            value = observed.get(field, "MISSING")
            expected_value = item[gold_field]
            checks.append({
                "pmcid":item["pmcid"], "field":field,
                "expected":expected_value, "observed":value,
                "passed":value.lower() == expected_value.lower(),
            })
    successes = sum(c["passed"] for c in checks)
    count = len(checks)
    return {
        "expected_trial_overlap": False,
        "assessed_labels": count,
        "correct_labels": successes,
        "label_match_rate": round(successes/count,4) if count else None,
        "metric_scope": "DOI/trial registration/study design/early-vs-advanced title triage ONLY",
        "not_a_clinical_accuracy_metric": True,
        "caveat": "Purposive tiny holdout; no confidence interval or population precision/recall claimed.",
        "checks": checks,
    }


def evaluate(manifest_path=MANIFEST, target="medical-affairs-agents/output/independent_holdout"):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if set(p["trial_id"] for p in manifest["holdout"]).intersection(manifest["train_trials"]):
        raise ValueError("Train-test trial leakage: holdout cannot be scored")
    results = []
    started = time.perf_counter()
    for entry in manifest["holdout"]:
        pmcid = entry["pmcid"]
        t0 = time.perf_counter()
        try:
            article = fingerprint(fetch(BASE+"/"+pmcid+"/fullTextXML"),pmcid)
            # The fingerprint uses article metadata + limited methods only.
            # Never extract/publish full text if rights are unclear.
            if article["license"]["status"]!="CC_BY_OR_CC0_CONFIRMED":
                article["status"]="BLOCKED_BY_LICENSE"
            else:
                article["status"]="SOURCE_METADATA_TRIAGED_REVIEW_REQUIRED"
            if article["doi"].lower() != entry["doi"].lower():
                article["status"]="BLOCKED_DOI_MISMATCH"
            if article["registration"] in manifest["train_trials"]:
                raise ValueError("Data leakage: source identifies training trial")
        except (OSError, ET.ParseError, ValueError, KeyError) as exc:
            article={"pmcid":pmcid,"status":"BLOCKED_FETCH_OR_PARSE_ERROR",
                     "error_type":type(exc).__name__}
        article["seconds"] = round(time.perf_counter()-t0,3)
        results.append(article)
        print("HOLDOUT",pmcid,article["status"],
              "DESIGN",article.get("design","UNKNOWN"),
              "SETTING",article.get("setting","UNKNOWN"),
              "LICENSE",article.get("license",{}).get("status","UNKNOWN"))
    metrics=score_holdout(results,manifest)
    metrics["runtime_seconds"]=round(time.perf_counter()-started,3)
    metrics["source_articles"]=results
    metrics["license_approved_count"]=sum(
        r.get("license",{}).get("status")=="CC_BY_OR_CC0_CONFIRMED" for r in results)
    out=Path(target)
    out.mkdir(parents=True,exist_ok=True)
    (out/"holdout_scorecard.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    lines=["# Frozen independent-trial holdout — predeclared evaluation", "",
           "**TROPION-Breast01 publications are excluded from this holdout.**",
           "Only paper identity, study registration, design and setting are scored.",
           "A pass does NOT validate extraction of effects, safety, causality, citations, or medical conclusions.",
           f"**Gold label matches:** {metrics['correct_labels']}/{metrics['assessed_labels']}.",
           f"**Conservatively license-approved:** {metrics['license_approved_count']}/{len(results)}.",
           f"**Elapsed (this stage only):** {metrics['runtime_seconds']:.3f} seconds.","",
           "| Holdout paper | Design | Setting | Trial registration | DOI match | License status |",
           "|---|---|---|---|---|---|"]
    for item in manifest["holdout"]:
        r=next((x for x in results if x["pmcid"]==item["pmcid"]),{})
        lines.append(f"| [{item['pmcid']}]({item['source']}) | {r.get('design','UNKNOWN')} "
                     f"| {r.get('setting','UNKNOWN')} | {r.get('registration','UNKNOWN')} "
                     f"| {'Yes' if r.get('doi')==item['doi'].lower() else 'NO'} "
                     f"| {r.get('license',{}).get('status','UNKNOWN')} |")
    lines+=["","## Why this is not a clinical accuracy score",
            "- The holdout has three purposively selected **independent** studies, not a representative random sample.",
            "- The scorer measures metadata and document triage, not effect sizes or biomedical inference.",
            "- Publications sharing an NCT ID cannot be split across development and holdout.",
            "- Observational evidence must not be presented as randomized causal evidence.",
            "- Unknown licenses or study types require human review rather than positive inference.",
            "- The manifest was committed separately before executing the benchmark.",
            "- Repeated tuning on these holdout results would invalidate their independent status.",
            "","## Development policy",
            "Freeze this V1 scorecard; use a *new* trial-family-disjoint V2 holdout for future evaluation.",
            "Curate outcome-level gold labels with a domain expert before quoting clinical precision/recall."]
    (out/"holdout_scorecard.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("HOLDOUT_LABEL_MATCHES",metrics["correct_labels"],"/",metrics["assessed_labels"])
    print("HOLDOUT_LICENSE_APPROVED",metrics["license_approved_count"],"/",len(results))
    print("HOLDOUT_RUNTIME_SECONDS",metrics["runtime_seconds"])
    return metrics


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="medical-affairs-agents/output/independent_holdout")
    args=p.parse_args()
    evaluate(target=args.out)
