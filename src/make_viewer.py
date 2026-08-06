# -*- coding: utf-8 -*-
"""Genera un visor HTML autocontenido con las 52 preguntas del EDA y sus figuras."""
from __future__ import annotations
import base64, html, json, os, re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
SRC = ROOT / "src"
FIGDIR = ROOT / "reportes" / "figuras"
OUT = ROOT / "reportes" / "EDA_Visor_52_Preguntas.html"

src = (SRC / "build_artifacts.py").read_text(encoding="utf-8")
prefix = src.split("assert len(questions) == 52")[0]
ns = {"__file__": str(SRC / "build_artifacts.py")}
exec(compile(prefix, "build_artifacts", "exec"), ns)
questions = ns["questions"]
groups = {int(k): v for k, v in re.findall(r'^\s+(\d+): "([^"]+)",',
          re.search(r"groups = \{(.*?)\n\}", src, re.S).group(1), re.M)}
figs = {int(k): v for k, v in re.findall(r'(\d+): "([^"]+)"',
        re.search(r"fig_after = \{(.*?)\}", src, re.S).group(1))}

CAPTIONS = {
    "01_serie_cif.png": "Serie mensual del valor CIF (2012-2024)",
    "02_distribucion_target.png": "Distribución de la variable objetivo",
    "03_correlaciones.png": "Matriz de correlaciones",
    "04_estacionalidad.png": "Estacionalidad por mes",
    "05_paises.png": "Principales países de origen",
}

def b64(name: str) -> str | None:
    p = FIGDIR / name
    if not p.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()

# --- construir tarjetas ---
cards, toc, current = [], [], None
for i, q in enumerate(questions, start=1):
    if i in groups:
        current = groups[i]
        toc.append(f'<a class="sec" href="#g{i}">{html.escape(current)}</a>')
        cards.append(f'<h2 class="grp" id="g{i}">{html.escape(current)}</h2>')
    fig_html = ""
    if i in figs:
        data = b64(figs[i])
        cap = CAPTIONS.get(figs[i], figs[i])
        fig_html = (f'<figure><img src="{data}" alt="{html.escape(cap)}">'
                    f'<figcaption>Figura · {html.escape(cap)}</figcaption></figure>'
                    ) if data else f'<p class="miss">Falta la figura {html.escape(figs[i])}</p>'
    cards.append(f"""
<article class="q" id="q{i}" data-txt="{html.escape((q['title']+' '+q['finding']+' '+q['implication']+' '+q['code']).lower())}">
  <header><span class="n">{i}</span><h3>{html.escape(q['title'])}</h3></header>
  <pre><code>{html.escape(q['code'])}</code></pre>
  <div class="f"><b>Hallazgo</b><p>{html.escape(q['finding'])}</p></div>
  <div class="i"><b>Implicación para el modelo</b><p>{html.escape(q['implication'])}</p></div>
  {fig_html}
</article>""")

page = f"""<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EDA · 52 preguntas · Importaciones Buenaventura</title>
<style>
:root{{--bg:#0f1216;--card:#171b21;--b:#242a33;--tx:#e6e9ee;--mu:#96a0ad;--ac:#5aa9ff;--ok:#3ecf8e;--wa:#f0b429}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--tx);font:15px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
header.top{{position:sticky;top:0;z-index:9;background:#0f1216ee;backdrop-filter:blur(8px);border-bottom:1px solid var(--b);padding:14px 24px}}
h1{{margin:0 0 2px;font-size:19px}} .sub{{color:var(--mu);font-size:13px}}
#s{{width:100%;max-width:420px;margin-top:10px;padding:9px 12px;border-radius:8px;border:1px solid var(--b);background:#11151a;color:var(--tx);font-size:14px}}
.wrap{{display:grid;grid-template-columns:250px 1fr;gap:28px;max-width:1180px;margin:0 auto;padding:22px 24px 80px}}
nav{{position:sticky;top:118px;align-self:start;font-size:13px}}
nav a.sec{{display:block;padding:7px 10px;color:var(--mu);text-decoration:none;border-left:2px solid var(--b);border-radius:0 6px 6px 0}}
nav a.sec:hover{{color:var(--ac);border-left-color:var(--ac);background:#1a1f26}}
h2.grp{{grid-column:1/-1;font-size:14px;letter-spacing:.09em;text-transform:uppercase;color:var(--ac);margin:34px 0 4px;padding-bottom:8px;border-bottom:1px solid var(--b)}}
article.q{{background:var(--card);border:1px solid var(--b);border-radius:12px;padding:18px 20px;margin:14px 0}}
article.q header{{display:flex;gap:12px;align-items:baseline}}
.n{{flex:none;width:30px;height:30px;border-radius:50%;background:#1e2a3a;color:var(--ac);display:grid;place-items:center;font-size:13px;font-weight:600}}
article.q h3{{margin:0;font-size:16px;font-weight:600}}
pre{{background:#0b0e12;border:1px solid var(--b);border-radius:8px;padding:11px 13px;overflow:auto;margin:12px 0}}
code{{font:12.5px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;color:#9fd0a8;white-space:pre}}
.f,.i{{border-left:3px solid var(--ok);padding:2px 0 2px 13px;margin:12px 0}}
.i{{border-left-color:var(--wa)}}
.f b,.i b{{display:block;font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--mu);margin-bottom:2px}}
.f p,.i p{{margin:0}}
figure{{margin:16px 0 0}} figure img{{width:100%;border-radius:10px;background:#fff;border:1px solid var(--b)}}
figcaption{{color:var(--mu);font-size:12.5px;margin-top:7px;text-align:center}}
.miss{{color:var(--wa);font-size:13px}}
.hide{{display:none}} #cnt{{color:var(--mu);font-size:13px;margin:8px 0 0}}
@media(max-width:820px){{.wrap{{grid-template-columns:1fr}}nav{{position:static}}}}
</style>
<header class="top">
  <h1>Análisis exploratorio · 52 preguntas</h1>
  <div class="sub">Importaciones registradas por la Aduana 35 de Buenaventura · DANE 2012-2024 · 5.625.947 registros · 156 meses</div>
  <input id="s" placeholder="Buscar por palabra, código o hallazgo…">
  <div id="cnt"></div>
</header>
<div class="wrap">
  <nav>{''.join(toc)}</nav>
  <main>{''.join(cards)}</main>
</div>
<script>
const s=document.getElementById('s'),cnt=document.getElementById('cnt'),
      qs=[...document.querySelectorAll('article.q')];
function upd(){{
  const t=s.value.trim().toLowerCase();
  let v=0;
  qs.forEach(a=>{{const m=!t||a.dataset.txt.includes(t);a.classList.toggle('hide',!m);if(m)v++;}});
  document.querySelectorAll('h2.grp').forEach(h=>{{
    let n=h.nextElementSibling,any=false;
    while(n&&n.tagName==='ARTICLE'){{if(!n.classList.contains('hide'))any=true;n=n.nextElementSibling;}}
    h.classList.toggle('hide',!any);
  }});
  cnt.textContent=t?v+' de '+qs.length+' preguntas coinciden':qs.length+' preguntas · 5 figuras';
}}
s.addEventListener('input',upd);upd();
</script></html>"""

OUT.write_text(page, encoding="utf-8")
print(f"OK -> {OUT}  ({OUT.stat().st_size/1024:.0f} KB, {len(questions)} preguntas, "
      f"{sum(1 for f in figs.values() if (FIGDIR/f).exists())}/{len(figs)} figuras incrustadas)")
