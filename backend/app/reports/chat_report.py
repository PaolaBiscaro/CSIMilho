"""Session storage and self-contained HTML for executive chat reports."""

from html import escape
from threading import RLock
from uuid import UUID

from app.harness.chat_contracts import ChatEnvelopeV2, InvestigativeChatResponse


class ChatReportStore:
    def __init__(self) -> None:
        self._items: dict[UUID, ChatEnvelopeV2] = {}
        self._lock = RLock()

    def save(self, report: ChatEnvelopeV2) -> None:
        if not isinstance(report.response, InvestigativeChatResponse):
            return
        with self._lock:
            self._items[report.turn_id] = report.model_copy(deep=True)

    def get(self, turn_id: UUID) -> ChatEnvelopeV2:
        with self._lock:
            if turn_id not in self._items:
                raise KeyError(turn_id)
            return self._items[turn_id].model_copy(deep=True)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


chat_report_store = ChatReportStore()


def _text(value) -> str:
    return escape(str(value), quote=True)


def _list(items, css="") -> str:
    return f'<ul class="{css}">' + "".join(f"<li>{_text(item)}</li>" for item in items) + "</ul>"


def _line_chart(chart_data) -> str:
    source = chart_data.field_ndvi or chart_data.ndvi
    if source is None or not source.series:
        return ""
    if chart_data.field_ndvi is not None:
        series = [(point.date, point.ndvi) for point in source.series]
        groups = [("NDVI", series)]
    else:
        groups = [
            ("Talhão analisado", [(point.date, point.target_ndvi) for point in source.series]),
            ("Referência", [(point.date, point.reference_ndvi) for point in source.series]),
        ]
    values = [float(value) for _, series in groups for _, value in series]
    low, high = min(values), max(values)
    span = high - low or 1.0
    width, height, pad = 760, 260, 34
    paths = []
    colors = ["#92552d", "#4e7650"]
    for index, (label, series) in enumerate(groups):
        points = []
        for pos, (_, value) in enumerate(series):
            x = pad + pos * (width - 2 * pad) / max(1, len(series) - 1)
            y = height - pad - (float(value) - low) * (height - 2 * pad) / span
            points.append(f"{x:.1f},{y:.1f}")
        paths.append(
            f'<polyline points="{" ".join(points)}" fill="none" stroke="{colors[index]}" '
            f'stroke-width="4"/><text x="{pad + index * 190}" y="24" fill="{colors[index]}">{_text(label)}</text>'
        )
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Série temporal de NDVI"><line x1="{pad}" y1="{height-pad}" x2="{width-pad}" '
        f'y2="{height-pad}" stroke="#cdb9aa"/>{"".join(paths)}</svg>'
    )


def render_chat_report(envelope: ChatEnvelopeV2) -> str:
    if not isinstance(envelope.response, InvestigativeChatResponse):
        raise ValueError("Somente investigações possuem relatório HTML.")
    response = envelope.response
    report = response.report
    answer = report.executive_answer
    insight_cards = "".join(
        f'<article><p class="kicker">Insight {index}</p><h3>{_text(item.claim)}</h3>'
        f'<p>{_text(item.interpretation)}</p><p class="support"><strong>Como chegamos aqui:</strong> '
        f'{_text(item.analytical_method)} — {_text(item.evidence_summary)}</p>'
        f'<p class="caveat"><strong>Limite:</strong> {_text(item.uncertainty)}</p></article>'
        for index, item in enumerate(report.insights, 1)
    )
    gaps = "" if not report.unanswered_parts else (
        '<section><h2>O que não pôde ser respondido</h2>' + "".join(
            f'<article><h3>{_text(item.question_part)}</h3><p>{_text(item.explanation)}</p>'
            f'<p><strong>O que seria necessário:</strong> {_text(item.requirement)}</p></article>'
            for item in report.unanswered_parts
        ) + "</section>"
    )
    hypotheses = "".join(
        f'<tr><td>{_text(item.question)}</td><td>{_text(item.method)}</td><td>{_text(item.status)}</td>'
        f'<td>{_text(item.p_value if item.p_value is not None else "—")}</td></tr>'
        for item in report.technical_appendix.hypotheses
    )
    limitations = "".join(
        f'<li><strong>{_text(item.title)}:</strong> {_text(item.explanation)} '
        f'<span>{_text(item.impact)}</span></li>' for item in report.limitations
    )
    chart = _line_chart(response.chart_data)
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{_text(answer.headline)} · FarmLab</title>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
<style>
:root{{--ink:#2d211a;--brown:#7d4726;--sand:#f3ece5;--line:#dccabd;--green:#4e7650}}*{{box-sizing:border-box}}
body{{margin:0;background:#f6f2ed;color:var(--ink);font:16px/1.62 system-ui,sans-serif}}main{{max-width:1040px;margin:auto;padding:40px 24px 80px}}
header{{background:var(--brown);color:white;padding:42px;border-radius:18px}}h1{{font-size:clamp(2rem,5vw,3.5rem);line-height:1.05;margin:.3rem 0}}
h2{{color:var(--brown);margin-top:2.4rem}}h3{{line-height:1.25}}section{{margin:30px 0}}article{{background:white;border:1px solid var(--line);border-radius:14px;padding:22px;margin:14px 0}}
.answer{{border-left:6px solid var(--brown);font-size:1.18rem}}.kicker{{text-transform:uppercase;letter-spacing:.09em;font-size:.76rem;font-weight:800;color:var(--brown)}}
.meta{{display:flex;gap:10px;flex-wrap:wrap}}.badge{{background:var(--sand);border-radius:999px;padding:6px 12px;font-weight:700}}.support,.caveat{{font-size:.93rem;color:#625249}}
.chart{{width:100%;height:auto;background:white;border:1px solid var(--line);border-radius:14px;padding:12px}}table{{width:100%;border-collapse:collapse;background:white}}
th,td{{padding:10px;border:1px solid var(--line);text-align:left;vertical-align:top}}th{{background:var(--sand)}}li span{{display:block;color:#6a5a50}}
@media(max-width:600px){{main{{padding:18px 12px 60px}}header{{padding:24px}}article{{padding:16px}}.table{{overflow:auto}}}}
@media print{{@page{{size:A4;margin:15mm}}body{{background:white;font-size:11pt}}main{{max-width:none;padding:0}}header{{border-radius:0;break-after:avoid}}article{{break-inside:avoid}}h2,h3{{break-after:avoid}}}}
</style></head><body><main><header><p class="kicker" style="color:white">Relatório executivo FarmLab</p><h1>{_text(answer.headline)}</h1>
<p>{_text(report.scope_summary)}</p></header><section><h2>Resposta</h2><article class="answer"><p>{_text(answer.answer)}</p>
<div class="meta"><span class="badge">Confiança: {_text(answer.confidence.value)}</span><span class="badge">Conclusão: {_text(answer.status.value)}</span></div>
<p class="caveat"><strong>Principal ressalva:</strong> {_text(answer.main_caveat)}</p></article></section>
<section><h2>Principais insights</h2>{insight_cards or '<p>Nenhum insight conclusivo foi sustentado.</p>'}</section>
{('<section><h2>Visualização</h2>' + chart + '</section>') if chart else ''}{gaps}
<section><h2>Detalhes técnicos</h2><div class="table"><table><thead><tr><th>Hipótese</th><th>Método</th><th>Status</th><th>p-valor</th></tr></thead><tbody>{hypotheses}</tbody></table></div>
<h3>Fontes utilizadas</h3>{_list(report.technical_appendix.source_files)}<h3>Limitações</h3><ul>{limitations}</ul></section>
</main></body></html>'''
