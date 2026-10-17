"""Conservative Portuguese causal-language rules with local disclaimer scope.

These lexical rules are not a general natural-language inference engine. An
uncertainty disclaimer only protects its own clause; a generic disclaimer in
another sentence/field never licenses a causal assertion.
"""

import re
import unicodedata

from app.harness.report_validation import ReportValidationIssue
from app.harness.schemas import InvestigationReport


class ReportLanguageError(ValueError):
    def __init__(self, issues: list[ReportValidationIssue]) -> None:
        self.issues = issues
        super().__init__("O relatório contém linguagem causal não sustentada por dados observacionais.")


def _normalize(text: str) -> str:
    # Remove accents and zero-width formatting, preserving word boundaries.
    normalized = "".join(char for char in unicodedata.normalize("NFKD", text.casefold())
                         if not unicodedata.combining(char) and unicodedata.category(char) != "Cf")
    return normalized.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


_RULES = tuple((name, re.compile(pattern)) for name, pattern in (
    ("causar", r"\b(?:causou|causaram|causa|causam|causar|causando|causaria|causariam|causara|causarao|causasse|causassem|causad[oa]s?)\b"),
    ("provar", r"\b(?:provou|provaram|prova|provam|provar|provaria|provara|provad[oa]s?|comprovou|comprovaram|comprova|comprovam|comprovar|comprovad[oa]s?)\b"),
    ("responsabilidade causal", r"\b(?:foi|foram|e|era|seria|sao|sera)\s+(?:diretamente\s+)?responsav(?:el|eis)\s+(?:por|pelo|pela|pelos|pelas)\b"),
    ("garantir", r"\b(?:garantiu|garantiram|garante|garantem|garantir|garantiria|garantira|garantirao|garantid[oa]s?)\b"),
    ("levar a", r"\b(?:levou|levaram|leva|levam|levaria|levara|levando|levar)\s+(?:diretamente\s+)?(?:a|ao|aos|as)\b"),
    ("provocar", r"\b(?:provocou|provocaram|provoca|provocam|provocar|provocaria|provocado|provocada)\b"),
    ("efeito causal", r"\b(?:efeitos?|relac(?:ao|oes)|nexos?|vinculos?)\s+causa(?:l|is)\b|\bcausalidade\s+(?:demonstrada|estabelecida|comprovada)\b"),
    ("atribuição direta", r"\b(?:resultado|consequencia)\s+diret[oa]\s+(?:de|do|da)\b"),
))

# Sentence boundaries, contrast and independent coordinated assertions reset
# the scope. A colon also resets scope; ambiguous quotations fail closed.
_CLAUSE = re.compile(
    r"[.!?;:\n]+|\b(?:mas|porem|contudo|entretanto|todavia|no entanto|apesar disso)\b|"
    r",\s*(?:e\s+)?(?=(?:o|a|os|as|isso|isto|esse|essa)\b)|"
    r"\be\s+(?=(?:sabemos|concluimos|afirmamos|constatamos|comprovamos|portanto)\b)|"
    r"\b(?:porque|pois)\b"
)
_EPISTEMIC_VERB = r"(?:afirmar|concluir|inferir|demonstrar|provar|comprovar|estabelecer|dizer|atribuir)"
_DISCLAIMER = re.compile(
    r"(?:\bnao\s+(?:e|foi|seria)\s+(?:possivel|correto|adequado|valido)\s+" + _EPISTEMIC_VERB + r"\s+(?:que|se)\b|"
    r"\bnao\s+(?:se\s+)?(?:pode|podemos|poderia)\s+" + _EPISTEMIC_VERB + r"\s+(?:que|se)\b|"
    r"\bnao\s+(?:permite|permitem|permitiu|sustenta|sustentam)\s+" + _EPISTEMIC_VERB + r"\s+(?:que|se)\b|"
    r"\bnao\s+ha\s+(?:evidencias?|provas?|base|suporte)(?:\s+suficientes?)?\s+(?:de|para)\s+(?:que\b|" + _EPISTEMIC_VERB + r"\s+que\b)|"
    r"\bsem\s+(?:evidencias?|provas?|base|suporte)(?:\s+suficientes?)?\s+para\s+" + _EPISTEMIC_VERB + r"\s+que\b|"
    r"\bnao\s+(?:provou|comprovou|demonstrou|demonstramos|comprovamos)\s+que\b)"
)
_DIRECT_LIMIT = re.compile(
    r"(?:\bnao\s+(?:(?:e|foi|seria)\s+(?:possivel|correto)\s+)?|\bsem\s+)"
    r"(?:concluir|afirmar|estabelecer|demonstrar|provar|comprovar|evidencias?\s+de|provas?\s+de)\s*$|"
    r"\bnao\s+(?:permite|permitem|podemos|se\s+pode)\s+(?:concluir|afirmar|estabelecer|demonstrar)\s*$"
)


def _is_disclaimed(clause: str, match: re.Match, family: str) -> bool:
    prefix = clause[:match.start()]
    # Explicit metalinguistic mentions of a single quoted expression are not
    # conclusions. Quoting an entire causal claim does not bypass validation.
    if re.search(r"\b(?:termo|palavra|expressao)\s+[\"']$", prefix) and clause[match.end():].startswith(('"', "'")):
        return True
    if family == "provar" and re.search(r"\b(?:nao|nunca)\s+$", prefix):
        return True  # "não provou" denies proof, not the causal effect itself.
    if family == "provar" and re.search(
        r"\b(?:nao ha|sem|ausencia de|nao e possivel|nao se pode|nao podemos|nao permite|nao permitem)\s+$", prefix
    ):
        return True
    if _DIRECT_LIMIT.search(prefix) and family in ("efeito causal", "provar"):
        return True
    disclaimers = list(_DISCLAIMER.finditer(prefix))
    if not disclaimers:
        return False
    tail = prefix[disclaimers[-1].end():]
    # Do not let double negation turn a denial of knowledge into a licence to
    # assert causality, or let a remote preamble govern an unbounded paragraph.
    if re.search(r"\b(?:negar|descartar|neguemos|impossivel)\b", tail):
        return False
    return len(tail.split()) <= 35


def _is_noncausal_use(clause: str, match: re.Match, family: str) -> bool:
    suffix = clause[match.end():]
    prefix = clause[:match.start()]
    if family == "causar" and match[0] == "causa":
        # Noun uses do not assert a known cause: "a causa é desconhecida".
        if re.match(r"\s+(?:e|permanece)\s+(?:desconhecida|incerta|indeterminada)\b", suffix):
            return True
        if re.search(r"\b(?:nao conhecemos|nao sabemos|nao e possivel determinar|nao e possivel identificar|investigar|identificar|verificar)\s+(?:a|uma)\s+$", prefix):
            return True
    if family == "levar a" and re.match(
        r"\s+(?:(?:o|a|os|as)\s+)?(?:equipe|tecnico|tecnica|tecnicos|tecnicas|amostra|amostras)\b", suffix
    ):
        # Literal transport, not "levou a equipe a concluir que...".
        return bool(re.match(r"\s+(?:(?:o|a|os|as)\s+)?\w+\s+(?:ao|a|para o|para a)\s+(?:campo|laboratorio|fazenda)\b", suffix))
    if family == "responsabilidade causal":
        return bool(re.search(r"\b(?:tecnico|tecnica|equipe|operador|operadora|analista)\s+$", prefix)
                    and re.match(r"\s+(?:conferir|registrar|coletar|organizar|revisar)\b", suffix))
    if family == "garantir":
        return bool(re.search(r"\b(?:pareamento|schema|validacao|harness|codigo)\s+$", prefix)
                    and re.match(r"\s+(?:(?:a|o|as|os)\s+)?(?:rastreabilidade|formato|datas comuns|mesmas datas|tipos)\b", suffix))
    return False


def validate_report_language(report: InvestigationReport) -> InvestigationReport:
    """Check every narrative field and return safe located errors for repair."""
    report = InvestigationReport.model_validate(report.model_dump())
    fields = [("overview.headline", report.overview.headline), ("overview.summary", report.overview.summary)]
    for section, names in (("findings", ("title", "explanation")),
                           ("limitations", ("title", "explanation")),
                           ("recommendations", ("action", "reason"))):
        for index, item in enumerate(getattr(report, section)):
            fields.extend((f"{section}[{index}].{name}", getattr(item, name)) for name in names)
    issues = []
    for location, text in fields:
        # Citations are metadata, not assertions or negation cues.
        text = re.sub(r"\bEV-[A-Z0-9-]+\b", " ", text)
        for clause in _CLAUSE.split(_normalize(text)):
            clause = re.sub(r"\s+", " ", clause)
            for family, pattern in _RULES:
                for match in pattern.finditer(clause):
                    if _is_disclaimed(clause, match, family) or _is_noncausal_use(clause, match, family):
                        continue
                    issue = ReportValidationIssue(
                        code="causal_language", location=location,
                        message=f"Revise a expressão da família '{family}': use linguagem descritiva/associativa ou uma ressalva explícita de impossibilidade de concluir causalidade na mesma oração.",
                    )
                    if issue not in issues:
                        issues.append(issue)
    if issues:
        raise ReportLanguageError(issues)
    return report
