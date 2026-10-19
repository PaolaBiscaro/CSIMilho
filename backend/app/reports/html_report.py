"""Script-free HTML from validated investigation output; no provider access."""
from datetime import timezone
from html import escape

from app.analytics.contracts import (
    ApplicationEvidence, ComparisonEvidence, NdviEvidence, SoilGroupsEvidence, SoilSummaryEvidence,
)
from app.harness.schemas import InvestigationResponse


CSP = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
STYLE = """
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f5f1eb;color:#36251b;font:16px/1.6 system-ui,sans-serif}
main{max-width:1120px;margin:auto;padding:32px}section,article{background:#fff;border:1px solid #dacdbf;border-radius:14px;padding:24px;margin:20px 0}
h1,h2,h3{line-height:1.2;color:#895129;overflow-wrap:anywhere}h1{font-size:2rem}nav{display:flex;gap:16px;flex-wrap:wrap}a{color:#78431f}
p,li,dd,td,th{overflow-wrap:anywhere}p{white-space:pre-wrap}.badge{font-weight:700;color:#895129}.notice{border-left:4px solid #895129;padding:12px;background:#faf5ee}
dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}dt{font-weight:700}dd{margin:0}.table-wrap{max-width:100%;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:.9rem}caption{text-align:left;font-weight:700;padding:12px 0}th,td{padding:9px;border:1px solid #dacdbf;text-align:left}th{background:#f4ede4}
:focus-visible{outline:3px solid #895129;outline-offset:3px}@media(max-width:600px){main{padding:12px}section,article{padding:16px}}
@media print{body{background:#fff}main{max-width:none;padding:0}nav{display:none}section,article{box-shadow:none}thead{display:table-header-group}.table-wrap{overflow:visible}h2,h3{break-after:avoid}}
"""
TOOLS = {
    "validate_comparison": "Validar comparabilidade", "compare_ndvi": "Comparar NDVI",
    "check_initial_condition": "Verificar condição inicial", "compare_population": "Comparar população",
    "application_compliance": "Conformidade de aplicação", "summarize_soil_analysis": "Resumo de solo",
    "compare_soil_measurement_groups": "Comparação de conjuntos de solo",
}


def value(item):
    if item is None:
        return "Indisponível"
    if isinstance(item, bool):
        return "Sim" if item else "Não"
    if isinstance(item, float):
        return f"{item:.4f}".rstrip("0").rstrip(".").replace(".", ",")
    return str(item)


def text(item):
    return escape(value(item), quote=True)


def paragraph(item, css=""):
    return f'<p class="{css}">{text(item)}</p>'


def metadata(items):
    return "<dl>" + "".join(f"<div><dt>{text(label)}</dt><dd>{text(item)}</dd></div>" for label, item in items) + "</dl>"


def table(caption, headings, rows):
    return ('<div class="table-wrap"><table><caption>' + text(caption) + '</caption><thead><tr>'
            + ''.join(f'<th scope="col">{text(label)}</th>' for label in headings) + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(f'<th scope="row">{text(cell)}</th>' if index == 0 else f'<td>{text(cell)}</td>'
                                      for index, cell in enumerate(row)) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def timestamp(item):
    return item.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")


def references(ids, anchors):
    return '<ul>' + ''.join(f'<li><a href="#{anchors[id_]}">{text(id_)}</a></li>' if id_ in anchors
                            else f'<li>{text(id_)} — evidência indisponível</li>' for id_ in ids) + '</ul>'


def evidence_html(item, anchor):
    parts = [f'<article id="{anchor}"><h3>{text(item.evidence_id)}</h3>']
    if isinstance(item, (SoilSummaryEvidence, SoilGroupsEvidence)):
        parts.append(paragraph("Solo: escopo geral do dataset, sem vínculo com talhão, coordenada, data ou profundidade. Conjuntos 1 e 2 não representam profundidades documentadas.", "notice"))
        parts.append(metadata([("Amostras", item.sample_count)]))
        if isinstance(item, SoilSummaryEvidence):
            group = "Conjunto 1" if item.measurement_group == "group_1" else "Conjunto 2"
            parts.append(metadata([("Conjunto", group), ("Completude (%)", item.completeness_percent),
                                   ("Valores válidos", item.valid_values), ("Valores esperados", item.expected_values)]))
            parts.append(table(f"Estatísticas · {group}", ["Métrica", "Unidade", "Válidas", "Ausentes", "Média", "Mín.", "Q1", "Mediana", "Q3", "Máx.", "Fontes"],
                               [[m.name, m.unit or "unidade não documentada", m.valid_n, m.missing_n, m.mean, m.min, m.q1, m.median, m.q3, m.max, ', '.join(m.source_files)] for m in item.metrics]))
            parts.append(metadata([("Textura válida", item.texture.valid_n), ("Textura excluída", item.texture.excluded_n)]))
            parts.append(table("Textura normalizada (%)", ["Amostra", "Areia", "Silte", "Argila", "Soma original"],
                               [[s.sample_id, s.sand, s.silt, s.clay, s.original_total] for s in item.texture.samples]))
            parts.append(paragraph(item.texture.method))
        else:
            parts.append(paragraph("Delta = Conjunto 2 − Conjunto 1."))
            for metric in item.metrics:
                parts.append(metadata([("Métrica", metric.name), ("Unidade", metric.unit or "unidade não documentada"),
                                       ("Pares válidos", metric.valid_n), ("Delta mediano", metric.median_delta)]))
                parts.append(table(f"Pares · {metric.name}", ["Amostra", "Conjunto 1", "Conjunto 2", "Delta 2 − 1"],
                                   [[p.sample_id, p.group_1, p.group_2, p.delta] for p in metric.pairs]))
        parts.extend(paragraph(limitation, "notice") for limitation in item.limitations)
    else:
        parts.append(metadata([("Talhão alvo", item.target_field_id), ("Talhão de referência", item.reference_field_id)]))
        parts.append(table("Valores consolidados", ["Métrica", "Alvo", "Referência", "Diferença", "Unidade"],
                           [[item.metric, item.target_value, item.reference_value, item.difference, item.unit or "unidade não documentada"]]))
        parts.append(paragraph("Diferença: alvo − referência. Na conformidade, a diferença é expressa em pontos percentuais."))
        if isinstance(item, NdviEvidence):
            parts.append(table("Série NDVI pareada", ["Data", "Alvo", "Referência", "Gap"],
                               [[p.date.strftime("%d/%m/%Y"), p.target_ndvi, p.reference_ndvi, p.gap] for p in item.series]))
        if isinstance(item, ComparisonEvidence):
            parts.append(metadata([("Permitida", item.allowed), ("Critérios atendidos", item.score), ("Total de critérios", item.max_score)]))
            parts.append(table("Comparabilidade", ["Critério", "Atendido", "Detalhe"], [[c.label, c.satisfied, c.detail] for c in item.criteria]))
        if isinstance(item, ApplicationEvidence):
            parts.append(paragraph(f"Operação: {item.operation}"))
            parts.append(table("Doses (kg/ha)", ["Talhão", "Aplicada", "Configurada"],
                               [["Alvo", item.target_applied_dose, item.target_configured_dose], ["Referência", item.reference_applied_dose, item.reference_configured_dose]]))
        if hasattr(item, "paired_dates"):
            parts.append(metadata([("Datas pareadas", item.paired_dates)]))
        if hasattr(item, "target_rows"):
            parts.append(table("Linhas utilizadas", ["Talhão", "Válidas", "Descartadas"],
                               [["Alvo", item.target_rows.valid, item.target_rows.discarded], ["Referência", item.reference_rows.valid, item.reference_rows.discarded]]))
    parts.append(metadata([("Observações", item.observation_count), ("Fontes", ', '.join(item.source_files)), ("Método", item.method), ("Versão", item.tool_version)]))
    parts.extend(paragraph(warning, "notice") for warning in item.warnings)
    return ''.join(parts) + '</article>'


def public_arguments(call):
    args = call.arguments
    if call.tool.value in ("summarize_soil_analysis", "compare_soil_measurement_groups"):
        items = [("Escopo", "Dataset, sem vínculo com talhão"), ("Métricas", ', '.join(args.metrics) if args.metrics is not None else "Todas as disponíveis")]
        if call.tool.value == "summarize_soil_analysis":
            items.append(("Conjunto", "Conjunto 1" if args.measurement_group == "group_1" else "Conjunto 2"))
    else:
        period = "Safra completa" if args.period == "full_season" else f"{args.period.start:%d/%m/%Y} a {args.period.end:%d/%m/%Y}"
        items = [("Talhão alvo", args.target_field_id), ("Talhão de referência", args.reference_field_id), ("Período", period)]
        if call.tool.value == "application_compliance":
            items.append(("Operação", args.operation))
    return items


def render_html_report(result: InvestigationResponse) -> str:
    report, trace = result.report, result.trace
    fallback = result.generated_by == "deterministic_fallback"
    origin = "Fallback determinístico · gerado localmente" if fallback else "Gemini"
    anchors = {item.evidence_id: f"evidence-{index}" for index, item in enumerate(result.evidence)}
    parts = ['<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             f'<meta http-equiv="Content-Security-Policy" content="{text(CSP)}">',
             f'<title>{text(report.overview.headline)} · FarmLab Investigator</title><style>{STYLE}</style></head><body><main>',
             '<header><p class="badge">FarmLab Investigator · Relatório da investigação</p>', f'<h1>{text(report.overview.headline)}</h1>',
             metadata([("Origem", origin), ("Modelo configurado", trace.model), ("Início", timestamp(trace.created_at)),
                       ("Investigação", result.investigation_id), ("Trace", trace.trace_id), ("Dataset", trace.dataset_id)]),
             '</header><nav aria-label="Seções do relatório"><a href="#overview">Visão geral</a><a href="#evidence">Evidências</a><a href="#limitations">Limitações</a><a href="#methods">Métodos</a></nav>',
             '<section id="overview"><h2>Visão geral</h2>', paragraph(report.overview.summary),
             metadata([("Força da evidência", {"weak": "Fraca", "moderate": "Moderada", "strong": "Forte"}[report.overview.evidence_strength])])]
    if fallback:
        parts.append(paragraph("Relatório produzido por templates locais. O modelo configurado não identifica o autor deste relatório.", "notice"))
    parts.append('<h2>Achados</h2>')
    for item in report.findings:
        parts.extend([f'<article><h3>{text(item.title)}</h3>', paragraph(item.explanation), references(item.evidence_ids, anchors), '</article>'])
    if not report.findings:
        parts.append(paragraph("Nenhum achado incluído."))
    parts.append('<h2>Recomendações</h2>')
    for item in report.recommendations:
        parts.extend([f'<article><h3>{text(item.action)}</h3><h4>Justificativa</h4>', paragraph(item.reason), references(item.evidence_ids, anchors), '</article>'])
    if not report.recommendations:
        parts.append(paragraph("Nenhuma recomendação incluída."))
    parts.append('</section><section id="evidence"><h2>Evidências</h2>')
    parts.append(paragraph("Tabelas autocontidas dos valores recebidos; nulos aparecem como Indisponível. Não são necessários scripts ou conexão à internet."))
    parts.extend(evidence_html(item, anchors[item.evidence_id]) for item in result.evidence)
    parts.append('</section><section id="limitations"><h2>Limitações</h2>')
    for item in report.limitations:
        parts.extend([f'<article><h3>{text(item.title)}</h3>', paragraph(item.explanation), paragraph(f"Regra associada: {item.rule_id}"), '</article>'])
    parts.append('</section><section id="methods"><h2>Métodos</h2>')
    for call in trace.calls:
        parts.extend([f'<article><h3>{text(call.sequence)} · {text(TOOLS[call.tool.value])}</h3>',
                      metadata([("Ferramenta", call.tool.value), ("Versão", call.tool_version), ("Estado", "Concluída" if call.status == "success" else "Falha"),
                                ("Início", timestamp(call.started_at)), ("Duração (ms)", call.duration_ms), ("Fontes", ', '.join(call.source_files) or "Nenhuma registrada"), *public_arguments(call)]),
                      references(call.result_evidence_ids, anchors)])
        if call.status == "error":
            parts.append(paragraph("A ferramenta não concluiu a execução.", "notice"))
        parts.append('</article>')
    if not trace.calls:
        parts.append(paragraph("Nenhuma execução de ferramenta registrada."))
    if trace.repair:
        parts.append('<h3>Reparo do relatório</h3>' + metadata([("Estado", "Concluído" if trace.repair.status == "success" else "Falha"),
                     ("Início", timestamp(trace.repair.started_at)), ("Duração (ms)", trace.repair.duration_ms)]))
    parts.append('</section><section><h2>Avisos</h2>')
    parts.extend(paragraph(warning.message, "notice") for warning in result.warnings)
    if not result.warnings:
        parts.append(paragraph("Nenhum aviso registrado."))
    parts.append('</section></main></body></html>')
    return ''.join(parts)
