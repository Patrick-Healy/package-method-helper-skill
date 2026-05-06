#!/usr/bin/env python3
"""Generate paper-layer cards from an acquired paper source bundle."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


LANGUAGE_DISPLAY = {"r": "R", "python": "Python", "stata": "Stata"}


PAPER_LAYER_SPECS: dict[tuple[str, str], dict[str, Any]] = {
    ("r", "matchit"): {
        "paper_title": "MatchIt: Nonparametric Preprocessing for Parametric Causal Inference",
        "paper_year": "2011",
        "paper_source_type": "software_paper",
        "keywords": ["matching", "causal inference", "preprocessing", "balance"],
        "method_concepts": ["matching", "causal_inference", "balance_diagnostics"],
        "decision_tags": ["adjustment_set", "sample_restriction", "estimand"],
        "summary": "The paper frames matching as a preprocessing step that improves the robustness of downstream parametric causal estimators.",
        "estimand": "A matched-sample causal contrast where the final estimand depends on the matching design and downstream outcome model.",
        "assumptions": [
            "selection on observables for the chosen covariate set",
            "balance diagnostics support the chosen matching specification",
            "the downstream estimator matches the target estimand after preprocessing",
        ],
        "function_links": [
            {"function": "matchit", "role": "construct matched samples under a chosen matching design"},
            {"function": "summary.matchit", "role": "inspect balance diagnostics after matching"},
        ],
        "student_queries": [
            "What does MatchIt treat as preprocessing rather than final estimation?",
            "How should matched samples connect to downstream regression?",
        ],
        "formalism": [
            "Matching defines a design stage that changes the support and weights used by the final outcome model.",
            "Balance and overlap matter before any outcome regression is interpreted causally.",
        ],
    },
    ("r", "plm"): {
        "paper_title": "Panel Data Econometrics in R: The plm Package",
        "paper_year": "2008",
        "paper_source_type": "software_paper",
        "keywords": ["panel data", "fixed effects", "random effects", "econometrics"],
        "method_concepts": ["panel_data", "fixed_effects", "random_effects"],
        "decision_tags": ["fixed_effects_scope", "cluster_level", "functional_form"],
        "summary": "The paper positions plm as a unified interface for classical panel-data estimators and inference workflows in R.",
        "estimand": "Panel-data regression parameters under within, random-effects, pooling, or first-difference transformations.",
        "assumptions": [
            "the panel estimator matches the data-generating structure and identifying assumptions",
            "unobserved heterogeneity is handled consistently with the chosen transformation",
            "standard error choices align with panel dependence and clustering patterns",
        ],
        "function_links": [
            {"function": "plm", "role": "estimate panel-data models under the chosen model specification"},
            {"function": "pdata.frame", "role": "prepare indexed panel data for estimation"},
        ],
        "student_queries": [
            "When should I use within versus random-effects in plm?",
            "How does plm encode panel indexing and transformations?",
        ],
        "formalism": [
            "Panel estimators can be expressed as transformations of the original model, such as within or first-difference operators.",
            "Inference depends on how serial and cross-sectional dependence are handled after transformation.",
        ],
    },
    ("r", "lavaan"): {
        "paper_title": "lavaan: An R Package for Structural Equation Modeling",
        "paper_year": "2012",
        "paper_source_type": "software_paper",
        "keywords": ["structural equation modeling", "confirmatory factor analysis", "latent variables"],
        "method_concepts": ["structural_equation_modeling", "latent_variables", "measurement_model"],
        "decision_tags": ["functional_form", "sample_restriction", "random_effects_structure"],
        "summary": "The paper explains lavaan as a formula-style interface for specifying and estimating latent-variable models in R.",
        "estimand": "Latent-variable model parameters implied by the specified measurement and structural equations.",
        "assumptions": [
            "the model specification correctly reflects the measurement and structural relationships",
            "identification conditions hold for the latent-variable model",
            "estimation and fit assessment are appropriate for the observed data and missingness structure",
        ],
        "function_links": [
            {"function": "cfa", "role": "estimate confirmatory factor analysis models"},
            {"function": "sem", "role": "estimate structural equation models under the declared specification"},
        ],
        "student_queries": [
            "What is identified automatically in lavaan and what still requires design justification?",
            "How should CFA and SEM entry points differ in practice?",
        ],
        "formalism": [
            "The package maps a declared system of latent-variable measurement and structural equations to an estimable covariance structure.",
            "Interpretation depends on identification, scaling, and fit diagnostics rather than syntax alone.",
        ],
    },
    ("r", "fixest"): {
        "paper_title": "Fast and user-friendly econometrics estimations: The R package fixest",
        "paper_year": "2026",
        "paper_source_type": "software_paper",
        "keywords": ["fixed effects", "instrumental variables", "difference in differences", "robust inference"],
        "method_concepts": ["fixed_effects", "instrumental_variables", "difference_in_differences"],
        "decision_tags": ["fixed_effects_scope", "cluster_level", "weights", "estimand"],
        "summary": "The paper presents fixest as a fast unified framework for applied econometric estimation with flexible fixed effects and inference choices.",
        "estimand": "Model-specific regression and treatment-effect parameters under the declared formula, fixed-effects structure, and inference design.",
        "assumptions": [
            "the specified identifying variation matches the econometric design",
            "fixed effects and controls are sufficient for the intended interpretation",
            "variance estimation choices such as clustering match the sampling and dependence structure",
        ],
        "function_links": [
            {"function": "feols", "role": "estimate linear models with optional fixed effects and robust inference"},
            {"function": "feglm", "role": "estimate generalized linear models with fixed effects under the chosen likelihood"},
        ],
        "student_queries": [
            "What econometric choices remain when using fixest beyond syntax?",
            "How should fixed effects and clustered inference be justified with feols?",
        ],
        "formalism": [
            "The package maps rich formula syntax to estimators with multiple fixed effects, optional IV structure, and post-estimation variance choices.",
            "The computational acceleration does not remove the need to justify estimands, controls, or inference design.",
        ],
    },
    ("python", "doubleml"): {
        "paper_title": "DoubleML - An Object-Oriented Implementation of Double Machine Learning in Python",
        "paper_year": "2022",
        "paper_source_type": "software_paper",
        "keywords": ["double machine learning", "orthogonalization", "causal inference", "nuisance models"],
        "method_concepts": ["causal_ml", "orthogonal_score", "double_machine_learning"],
        "decision_tags": ["adjustment_set", "estimand", "functional_form"],
        "summary": "The paper formalizes how DoubleML operationalizes Neyman-orthogonal scores and sample splitting for causal estimation.",
        "estimand": "Causal parameters identified by orthogonal score functions after nuisance components are estimated with machine learning.",
        "assumptions": [
            "the chosen score corresponds to the target causal parameter",
            "nuisance learners achieve sufficient predictive quality for the orthogonal moment conditions",
            "cross-fitting and sample splitting are configured consistently with the design",
        ],
        "function_links": [
            {"function": "DoubleMLPLR", "role": "estimate partially linear regression treatment effects under orthogonal moments"},
            {"function": "DoubleMLIRM", "role": "estimate interactive regression treatment effects with cross-fitting"},
        ],
        "student_queries": [
            "What does DoubleML estimate versus what is chosen by the researcher?",
            "How should nuisance models be justified in a DML workflow?",
        ],
        "formalism": [
            "The estimator targets causal parameters through orthogonal score equations combined with cross-fitted nuisance estimates.",
            "Machine-learning flexibility enters through nuisance components, not through a free-form causal estimand.",
        ],
    },
    ("python", "statsmodels"): {
        "paper_title": "Statsmodels: Econometric and Statistical Modeling with Python",
        "paper_year": "2010",
        "paper_source_type": "software_paper",
        "keywords": ["econometrics", "statistics", "python", "modeling"],
        "method_concepts": ["econometrics", "statistical_modeling", "inference"],
        "decision_tags": ["functional_form", "cluster_level", "sample_restriction"],
        "summary": "The paper explains statsmodels as a Python framework for classical statistical and econometric modeling with explicit inference objects.",
        "estimand": "Model-specific parameters and inferential objects defined by the chosen model class and formula or design matrix.",
        "assumptions": [
            "the chosen model class matches the statistical structure of the problem",
            "identification and inferential assumptions are justified outside the library interface",
            "robustness choices such as covariance type match the data dependence structure",
        ],
        "function_links": [
            {"function": "statsmodels.formula.api.ols", "role": "fit classical linear models with formula syntax"},
            {"function": "statsmodels.api.OLS", "role": "fit linear models from explicit design matrices and access inference objects"},
        ],
        "student_queries": [
            "What does statsmodels provide beyond model fitting syntax?",
            "How should covariance choices and inference be justified when using statsmodels?",
        ],
        "formalism": [
            "Statsmodels exposes model classes and results objects that separate estimation, diagnostics, and inference.",
            "The package supports many estimators, but the causal or statistical interpretation still depends on model choice and assumptions.",
        ],
    },
    ("stata", "boottest"): {
        "paper_title": "Fast and wild: Bootstrap inference in Stata using boottest",
        "paper_year": "2019",
        "paper_source_type": "methods_paper",
        "keywords": ["wild bootstrap", "cluster-robust inference", "stata", "hypothesis testing"],
        "method_concepts": ["bootstrap_inference", "cluster_robust_se", "hypothesis_testing"],
        "decision_tags": ["cluster_level", "weights", "estimand"],
        "summary": "The paper explains boottest as an efficient implementation of wild bootstrap inference for linear restrictions in Stata estimation workflows.",
        "estimand": "Test statistics and p-values for linear hypotheses evaluated with wild bootstrap procedures under the chosen estimation design.",
        "assumptions": [
            "the bootstrap design is appropriate for the estimator and dependence structure",
            "the clustering level is aligned with the data-generating process",
            "the tested hypothesis corresponds to a substantively meaningful parameter restriction",
        ],
        "function_links": [
            {"function": "boottest", "role": "compute wild-bootstrap inference for linear restrictions after estimation"},
            {"function": "waldtest", "role": "compare bootstrap-based and conventional restriction testing logic when relevant"},
        ],
        "student_queries": [
            "When is boottest preferable to asymptotic cluster-robust inference?",
            "What bootstrap choices still require justification after estimation?",
        ],
        "formalism": [
            "Bootstrap inference targets the sampling distribution of test statistics under resampled score or residual structures.",
            "The package changes the inferential approximation, not the underlying estimand defined by the fitted model.",
        ],
    },
}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_paper_root = script_dir.parents[2] / "work" / "generated" / "paper_acquisition"
    default_output = script_dir.parents[2] / "work" / "generated" / "paper_layers"
    parser = argparse.ArgumentParser(description="Generate paper-layer cards from paper source bundles.")
    parser.add_argument("--language", required=True, choices=("r", "python", "stata"))
    parser.add_argument("--package", required=True)
    parser.add_argument("--paper-source-root", type=Path, default=default_paper_root)
    parser.add_argument("--output-root", type=Path, default=default_output)
    parser.add_argument("--package-manifest", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def _norm_text(value: Any) -> str:
    return str(value or "").strip()


def _slug(value: str) -> str:
    text = _norm_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def extract_section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    capture = False
    collected: list[str] = []
    target = heading.strip().lower()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current = stripped[3:].strip().lower()
            if capture and current != target:
                break
            capture = current == target
            continue
        if capture:
            collected.append(line)
    text = "\n".join(collected).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def first_sentence(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return "review required"
    match = re.search(r"(.+?[.!?])\s", clean)
    if match:
        return match.group(1).strip()
    return clean


def infer_year(manifest: dict[str, Any], markdown: str) -> str:
    for candidate in [
        _norm_text((manifest.get("paper") or {}).get("title")),
        _norm_text(manifest.get("selected_paper_url")),
        markdown,
    ]:
        match = re.search(r"\b(19|20)\d{2}\b", candidate)
        if match:
            return match.group(0)
    return ""


def load_package_manifest(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return load_json(path)


def related_chunks(language: str, package: str, top_functions: list[str]) -> list[str]:
    lang = _slug(language)
    pkg = _slug(package)
    items = [
        f"overview_{lang}_{pkg}",
        f"decision_{lang}_{pkg}",
        f"pattern_{lang}_{pkg}",
        f"doc_{lang}_{pkg}_001",
    ]
    for func in top_functions[:2]:
        items.append(f"function_{lang}_{pkg}_{_slug(func)}")
    return items


def infer_top_functions(manifest: dict[str, Any] | None) -> list[str]:
    if not manifest:
        return []
    rag = manifest.get("rag_agent") or {}
    funcs = rag.get("top_functions_or_commands") or []
    return [str(item).strip() for item in funcs if str(item).strip()]


def build_runtime_spec(
    language: str,
    package: str,
    paper_manifest: dict[str, Any],
    paper_markdown: str,
    package_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    key = (language.lower(), package.lower())
    spec = dict(PAPER_LAYER_SPECS.get(key, {}))
    abstract = extract_section(paper_markdown, "Abstract")
    if not spec.get("paper_title"):
        spec["paper_title"] = _norm_text((paper_manifest.get("paper") or {}).get("title")) or package
    if not spec.get("paper_year"):
        spec["paper_year"] = infer_year(paper_manifest, paper_markdown)
    if not spec.get("paper_source_type"):
        spec["paper_source_type"] = _norm_text(paper_manifest.get("paper_source_type")) or "methods_paper"
    if not spec.get("keywords"):
        spec["keywords"] = [package]
    if not spec.get("method_concepts"):
        spec["method_concepts"] = []
    if not spec.get("decision_tags"):
        spec["decision_tags"] = []
    if not spec.get("summary"):
        spec["summary"] = first_sentence(abstract)
    if not spec.get("estimand"):
        spec["estimand"] = "review required"
    if not spec.get("assumptions"):
        spec["assumptions"] = ["review required", "review required", "review required"]
    top_functions = infer_top_functions(package_manifest)
    if not spec.get("function_links"):
        if top_functions:
            spec["function_links"] = [
                {"function": func, "role": "primary package entry point for the documented method"}
                for func in top_functions[:2]
            ]
        else:
            spec["function_links"] = [{"function": package, "role": "primary package entry point"}]
    if not spec.get("student_queries"):
        spec["student_queries"] = [
            f"What does the {package} paper contribute beyond the package docs?",
            f"Which assumptions from the {package} paper must be justified in applied work?",
        ]
    if not spec.get("formalism"):
        spec["formalism"] = [
            spec["estimand"] if spec.get("estimand") else "review required",
            "Map the formal estimand and assumptions back to package entry points before writing code.",
        ]
    spec["paper_source_url"] = _norm_text(paper_manifest.get("selected_paper_url"))
    spec["open_doc_url"] = _norm_text(paper_manifest.get("selected_paper_url") or "")
    return spec


def build_paper_note_text(language: str, package: str, canonical_name: str, spec: dict[str, Any], related: list[str]) -> str:
    lines = [
        "[TYPE] paper_note",
        f"[LANGUAGE] {LANGUAGE_DISPLAY[language]}",
        f"[PACKAGE] {package}",
        f"[CANONICAL_PACKAGE] {canonical_name}",
        f"[TITLE] {spec.get('paper_title') or ''}",
        f"[PAPER_YEAR] {spec.get('paper_year') or ''}",
        f"[PAPER_SOURCE_TYPE] {spec.get('paper_source_type') or ''}",
        f"[PAPER_SOURCE_URL] {spec.get('paper_source_url') or ''}",
        f"[OPEN_DOC_URL] {spec.get('open_doc_url') or ''}",
        f"[KEYWORDS] {', '.join(spec.get('keywords') or [])}",
        "[RETRIEVAL_PRIORITY] method_theory",
        "[UPLOAD_TIER] supplementary_context",
        f"[METHOD_CONCEPTS] {', '.join(spec.get('method_concepts') or [])}",
        f"[DECISION_TAGS] {', '.join(spec.get('decision_tags') or [])}",
        "",
        "What This Paper Adds:",
        f"- {spec.get('summary') or 'review required'}",
        "",
        "Estimand Or Formal Target:",
        f"- {spec.get('estimand') or 'review required'}",
        "",
        "Key Assumptions:",
    ]
    lines.extend(f"- {item}" for item in (spec.get("assumptions") or []))
    lines.extend(["", "Mapped Entry Points:"])
    lines.extend(f"- {item.get('function')}: {item.get('role')}" for item in (spec.get("function_links") or []))
    lines.extend(["", "Good Theory Questions:"])
    lines.extend(f"- {item}" for item in (spec.get("student_queries") or []))
    lines.extend(["", "Related Chunks:"])
    lines.extend(f"- {item}" for item in related)
    return "\n".join(lines).strip() + "\n"


def build_equation_note_text(language: str, package: str, canonical_name: str, spec: dict[str, Any], related: list[str]) -> str:
    lines = [
        "[TYPE] equation_note",
        f"[LANGUAGE] {LANGUAGE_DISPLAY[language]}",
        f"[PACKAGE] {package}",
        f"[CANONICAL_PACKAGE] {canonical_name}",
        f"[TITLE] {spec.get('paper_title') or ''}",
        f"[PAPER_SOURCE_URL] {spec.get('paper_source_url') or ''}",
        f"[OPEN_DOC_URL] {spec.get('open_doc_url') or ''}",
        f"[KEYWORDS] {', '.join(spec.get('keywords') or [])}",
        "[RETRIEVAL_PRIORITY] method_theory",
        "[UPLOAD_TIER] supplementary_context",
        f"[METHOD_CONCEPTS] {', '.join(spec.get('method_concepts') or [])}",
        f"[DECISION_TAGS] {', '.join(spec.get('decision_tags') or [])}",
        "",
        "Formalism To Retrieve:",
    ]
    lines.extend(f"- {item}" for item in (spec.get("formalism") or []))
    lines.extend(["", "Interpretation For Package Users:", f"- {spec.get('estimand') or 'review required'}", "", "Function Mapping:"])
    lines.extend(f"- {item.get('function')}: {item.get('role')}" for item in (spec.get("function_links") or []))
    lines.extend(["", "Related Chunks:"])
    lines.extend(f"- {item}" for item in related)
    return "\n".join(lines).strip() + "\n"


def build_method_bridge_card_text(language: str, package: str, canonical_name: str, spec: dict[str, Any], related: list[str]) -> str:
    lines = [
        "[TYPE] method_bridge_card",
        f"[LANGUAGE] {LANGUAGE_DISPLAY[language]}",
        f"[PACKAGE] {package}",
        f"[CANONICAL_PACKAGE] {canonical_name}",
        f"[TITLE] {spec.get('paper_title') or ''}",
        f"[PAPER_SOURCE_URL] {spec.get('paper_source_url') or ''}",
        f"[OPEN_DOC_URL] {spec.get('open_doc_url') or ''}",
        f"[KEYWORDS] {', '.join(spec.get('keywords') or [])}",
        "[RETRIEVAL_PRIORITY] method_theory",
        "[UPLOAD_TIER] supplementary_context",
        f"[METHOD_CONCEPTS] {', '.join(spec.get('method_concepts') or [])}",
        f"[DECISION_TAGS] {', '.join(spec.get('decision_tags') or [])}",
        "",
        "Bridge From Paper To Package:",
    ]
    lines.extend(f"- {item.get('function')}: {item.get('role')}" for item in (spec.get("function_links") or []))
    lines.extend([
        "",
        "How To Use This Bridge:",
        "- Use the paper note for estimands and assumptions.",
        "- Use the equation note for the formal objects and notation.",
        "- Use the mapped function cards for syntax and defaults.",
        "",
        "Related Chunks:",
    ])
    lines.extend(f"- {item}" for item in related)
    return "\n".join(lines).strip() + "\n"


def update_manifest_copy(package_manifest: dict[str, Any], output_dir: Path) -> Path:
    updated = json.loads(json.dumps(package_manifest))
    content_presence = updated.setdefault("content_presence", {})
    status = updated.setdefault("status", {})
    content_presence["paper_card_count"] = 3
    status["has_paper_layer"] = True
    outpath = output_dir / "updated_package_manifest.json"
    outpath.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n")
    return outpath


def main() -> int:
    args = parse_args()
    language = args.language.lower()
    package = _norm_text(args.package)
    paper_dir = args.paper_source_root / language / package
    paper_manifest = load_json(paper_dir / "paper_source_manifest.json")
    paper_markdown = (paper_dir / "paper_source.md").read_text()
    package_manifest = load_package_manifest(args.package_manifest)
    canonical_name = _norm_text((package_manifest or {}).get("canonical_package_name")) or package
    spec = build_runtime_spec(language, package, paper_manifest, paper_markdown, package_manifest)
    top_functions = [item.get("function", "") for item in (spec.get("function_links") or []) if item.get("function")]
    related = related_chunks(language, package, top_functions)

    outdir = args.output_root / language / package
    outdir.mkdir(parents=True, exist_ok=True)
    paper_path = outdir / f"paper_{_slug(language)}_{_slug(package)}.md"
    equation_path = outdir / f"equation_{_slug(language)}_{_slug(package)}.md"
    bridge_path = outdir / f"bridge_{_slug(language)}_{_slug(package)}.md"
    paper_path.write_text(build_paper_note_text(language, package, canonical_name, spec, related))
    equation_path.write_text(build_equation_note_text(language, package, canonical_name, spec, related))
    bridge_path.write_text(build_method_bridge_card_text(language, package, canonical_name, spec, related))

    manifest_update_path = None
    if package_manifest:
        manifest_update_path = update_manifest_copy(package_manifest, outdir)

    layer_manifest = {
        "workflow_version": "1.0",
        "language": language,
        "package": package,
        "canonical_package_name": canonical_name,
        "paper_source_manifest_path": str(paper_dir / "paper_source_manifest.json"),
        "generated_files": {
            "paper_note": str(paper_path),
            "equation_note": str(equation_path),
            "method_bridge_card": str(bridge_path),
        },
        "updated_package_manifest_path": str(manifest_update_path) if manifest_update_path else "",
        "paper_source_type": spec.get("paper_source_type"),
        "paper_source_url": spec.get("paper_source_url"),
    }
    (outdir / "paper_layer_manifest.json").write_text(json.dumps(layer_manifest, indent=2, ensure_ascii=False) + "\n")

    if args.json:
        print(json.dumps({"status": "ok", "output_dir": str(outdir), "manifest": layer_manifest}, indent=2))
    else:
        print(f"Wrote paper layer bundle to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
