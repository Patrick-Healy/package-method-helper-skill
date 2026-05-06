[TYPE] function_card
[LANGUAGE] {Language}
[PACKAGE] {package}
[CANONICAL_PACKAGE] {package}
[FUNCTION_OR_COMMAND] {func}
[TITLE] {func}
[KEYWORDS] {func}, {package}
[ROLE_CLASS] {role_class}
[AGENT_SAFETY_CLASS] {safety_class}
[TASK_TAGS] {task_tags}
[COMMON_PAIRINGS] {pairings}
[RETRIEVAL_PRIORITY] {priority}
[UPLOAD_TIER] supplementary_context
[METHOD_CONCEPTS] {concepts}
[DECISION_TAGS] {tags}
[OPEN_DOC_URL] {func_doc_url}

What This Function Or Command Is For:
- {description}

Student Lookup Prompts:
- How do I use {func} in {package}?
- What choices should I surface when using {func}?

Do Not Use This For:
- {guidance}

What Is Not Automatic:
- This page documents the entry point, not the full empirical design or identification strategy.

Researcher Decisions To Surface:
- {tag1}
- {tag2}

Example User Queries:
- How do I use {func} in {package}?
- {query2}

Related Chunks:
- overview_{lang}_{package}
- function_doc_{lang}_{package}_{func}
- doc_{lang}_{package}_001

---
# {package}::{func} ({Language} function doc)

Source: {url}

{full_function_help_page_content}
