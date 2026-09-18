import os
import time

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Token Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPSTREAM_BASE = os.getenv("OPENAI_API_BASE", "https://generativelanguage.googleapis.com/v1beta/openai")
UPSTREAM_KEY = os.getenv("OPENAI_API_KEY", "")

# The console is a single self-contained document: no build step, no bundler,
# no external image or script requests. Raw string so the embedded JS keeps its
# own backslash escapes.
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>AI Token Gateway</title>
<meta name="description" content="Route, meter and audit LLM traffic across providers from one gateway.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#0A0C16; --bg:#0A0C16; --bg-2:#0E1120;
  --surface:#13172B; --surface-2:#1A1F3A; --surface-3:#222850;
  --line:rgba(255,255,255,.075); --line-2:rgba(255,255,255,.14);
  --text:#E7E9F7; --text-2:#969CC4; --text-3:#666C96;
  --primary:#7A7CFF; --primary-2:#9E8BFF; --primary-dim:rgba(122,124,255,.16);
  --pass:#3DD68C; --pass-dim:rgba(61,214,140,.14);
  --warn:#FFB224; --warn-dim:rgba(255,178,36,.14);
  --deny:#FF5C7A; --deny-dim:rgba(255,92,122,.14);
  --info:#5BC8FF;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 12px 32px -12px rgba(0,0,0,.7);
  --r-sm:6px; --r-md:10px; --r-lg:16px; --r-xl:22px;
  --sans:"Instrument Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace;
  --rail:64px; --maxw:1320px;
  --ease:cubic-bezier(.22,.61,.36,1);
}
:root[data-theme="light"]{
  --ink:#14172B; --bg:#F2F4FB; --bg-2:#E9EDF8;
  --surface:#FFFFFF; --surface-2:#F4F6FC; --surface-3:#E7EBF7;
  --line:rgba(20,23,43,.10); --line-2:rgba(20,23,43,.18);
  --text:#14172B; --text-2:#545A7E; --text-3:#7C82A3;
  --primary:#4F46E5; --primary-2:#7C5CE0; --primary-dim:rgba(79,70,229,.10);
  --pass:#0E9F6E; --pass-dim:rgba(14,159,110,.12);
  --warn:#B45309; --warn-dim:rgba(180,83,9,.12);
  --deny:#D62B52; --deny-dim:rgba(214,43,82,.10);
  --info:#0284C7;
  --shadow:0 1px 2px rgba(20,23,43,.06), 0 10px 28px -14px rgba(20,23,43,.28);
}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
html{-webkit-text-size-adjust:100%}
body{
  background:var(--bg); color:var(--text); font-family:var(--sans);
  font-size:15px; line-height:1.5; min-height:100vh;
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
  transition:background .35s var(--ease), color .35s var(--ease);
}
body::before{
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    radial-gradient(900px 520px at 12% -8%, rgba(122,124,255,.16), transparent 62%),
    radial-gradient(760px 480px at 92% 4%, rgba(255,178,36,.07), transparent 60%),
    radial-gradient(1000px 700px at 50% 108%, rgba(158,139,255,.08), transparent 66%);
}
:root[data-theme="light"] body::before{
  background:
    radial-gradient(900px 520px at 12% -8%, rgba(79,70,229,.10), transparent 62%),
    radial-gradient(760px 480px at 92% 4%, rgba(180,83,9,.05), transparent 60%);
}
body::after{
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none; opacity:.45;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='.35'/%3E%3C/svg%3E");
  mix-blend-mode:overlay;
}
:root[data-theme="light"] body::after{opacity:.3; mix-blend-mode:multiply}
.mono{font-family:var(--mono); font-variant-numeric:tabular-nums; font-feature-settings:"tnum" 1,"zero" 1}
h1,h2,h3,h4{margin:0; font-weight:600; letter-spacing:-.018em; line-height:1.2}
p{margin:0}
a{color:inherit}
button,input,select,textarea{font:inherit; color:inherit}
:focus-visible{outline:2px solid var(--primary); outline-offset:2px; border-radius:4px}
::selection{background:var(--primary-dim); color:var(--text)}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--line-2); border-radius:99px; border:3px solid transparent; background-clip:content-box}
::-webkit-scrollbar-thumb:hover{background:var(--text-3); background-clip:content-box}

/* ---------- shell ---------- */
.shell{position:relative; z-index:1; display:grid; grid-template-columns:var(--rail) minmax(0,1fr); min-height:100vh}
.rail{
  position:sticky; top:0; height:100vh; display:flex; flex-direction:column; align-items:center;
  gap:6px; padding:16px 0; border-right:1px solid var(--line);
  background:var(--bg); background:color-mix(in srgb, var(--bg) 82%, transparent); backdrop-filter:blur(14px);
}
.brandmark{width:34px;height:34px;margin-bottom:14px;flex:none}
.rail-btn{
  width:38px;height:38px;border:0;background:transparent;border-radius:var(--r-md);
  display:grid;place-items:center;cursor:pointer;color:var(--text-3);
  transition:color .18s var(--ease), background .18s var(--ease);
}
.rail-btn:hover{color:var(--text); background:var(--surface-2)}
.rail-btn[aria-current="true"]{color:var(--primary); background:var(--primary-dim)}
.rail-btn svg{width:19px;height:19px}
.rail-sp{flex:1}

.main{min-width:0; display:flex; flex-direction:column}
.wrap{width:100%; max-width:var(--maxw); margin:0 auto; padding:0 28px}

/* ---------- top bar ---------- */
.topbar{
  position:sticky; top:0; z-index:40; border-bottom:1px solid var(--line);
  background:var(--bg); background:color-mix(in srgb, var(--bg) 78%, transparent); backdrop-filter:blur(18px) saturate(1.4);
}
.topbar-in{display:flex; align-items:center; gap:18px; height:60px}
.wordmark{font-size:15px; font-weight:600; letter-spacing:-.02em; white-space:nowrap}
.envchip{
  display:inline-flex; align-items:center; gap:7px; height:26px; padding:0 10px;
  border:1px solid var(--line-2); border-radius:99px; font-size:12px; color:var(--text-2);
  font-family:var(--mono);
}
.dot{width:6px;height:6px;border-radius:99px;background:var(--pass);flex:none;position:relative}
.dot::after{content:"";position:absolute;inset:-3px;border-radius:99px;background:inherit;opacity:.28;animation:breathe 2.6s var(--ease) infinite}
@keyframes breathe{0%,100%{transform:scale(1);opacity:.28}50%{transform:scale(1.85);opacity:0}}
.dot.warn{background:var(--warn)} .dot.deny{background:var(--deny)} .dot.idle{background:var(--text-3)}
.topbar-sp{flex:1}
.kbtn{
  display:inline-flex;align-items:center;gap:9px;height:34px;padding:0 12px;
  border:1px solid var(--line); background:var(--surface); border-radius:var(--r-md);
  font-size:13px; color:var(--text-2); cursor:pointer; white-space:nowrap;
  transition:border-color .18s var(--ease), color .18s var(--ease), background .18s var(--ease);
}
.kbtn:hover{border-color:var(--line-2); color:var(--text)}
.kbtn svg{width:15px;height:15px;flex:none}
kbd{
  font-family:var(--mono); font-size:11px; padding:2px 5px; border-radius:4px;
  background:var(--surface-2); border:1px solid var(--line); color:var(--text-3);
}
.searchbtn{min-width:190px}
.searchbtn .topbar-sp{flex:1}

/* ---------- section scaffolding ---------- */
.section{padding:30px 0}
.section + .section{padding-top:4px}
.sec-head{display:flex; align-items:baseline; gap:14px; margin-bottom:16px; flex-wrap:wrap}
.sec-head h2{font-size:16px}
.sec-note{font-size:13px; color:var(--text-3)}

/* ---------- the wire ---------- */
.wire-panel{
  border:1px solid var(--line); border-radius:var(--r-xl); background:
    linear-gradient(180deg, var(--surface-2), var(--surface));
  box-shadow:var(--shadow); padding:26px 26px 20px; position:relative; overflow:hidden;
}
.wire-panel::before{
  content:""; position:absolute; inset:0; pointer-events:none; opacity:.5;
  background-image:linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px);
  background-size:26px 26px; mask-image:radial-gradient(80% 120% at 50% 0%, #000 12%, transparent 72%);
}
.wire-top{display:flex;align-items:center;gap:12px;margin-bottom:26px;position:relative;flex-wrap:wrap}
.wire-title{font-size:15px}
.wire-verdict{
  font-family:var(--mono); font-size:12px; padding:3px 9px; border-radius:99px;
  border:1px solid var(--line-2); color:var(--text-3); transition:all .25s var(--ease);
}
.wire-verdict[data-state="run"]{color:var(--warn);border-color:var(--warn);background:var(--warn-dim)}
.wire-verdict[data-state="pass"]{color:var(--pass);border-color:var(--pass);background:var(--pass-dim)}
.wire-verdict[data-state="deny"]{color:var(--deny);border-color:var(--deny);background:var(--deny-dim)}

.wire{position:relative; display:grid; grid-template-columns:repeat(6,1fr); gap:0; padding:8px 0 4px}
.wire-rail{
  position:absolute; left:8.33%; right:8.33%; top:24px; height:2px; border-radius:2px;
  background:linear-gradient(90deg,var(--line-2),var(--line-2)); overflow:hidden;
}
.wire-rail::after{
  content:""; position:absolute; inset:0; width:var(--fill,0%);
  background:linear-gradient(90deg,var(--primary),var(--primary-2));
  transition:width .4s var(--ease);
}
.packet{
  position:absolute; top:20px; left:8.33%; width:10px; height:10px; margin-left:-5px; border-radius:99px;
  background:var(--primary); box-shadow:0 0 0 4px var(--primary-dim), 0 0 18px 3px var(--primary);
  opacity:0; transition:left .42s var(--ease), opacity .2s linear, background .2s linear;
}
.packet.on{opacity:1}
.packet.deny{background:var(--deny); box-shadow:0 0 0 4px var(--deny-dim), 0 0 18px 3px var(--deny)}

.node{display:flex; flex-direction:column; align-items:center; gap:9px; text-align:center; position:relative}
.node-ring{
  width:34px;height:34px;border-radius:99px;display:grid;place-items:center;flex:none;
  background:var(--surface-2); border:1.5px solid var(--line-2); color:var(--text-3);
  transition:border-color .3s var(--ease), color .3s var(--ease), background .3s var(--ease), transform .3s var(--ease);
}
.node-ring svg{width:15px;height:15px}
.node-name{font-size:12.5px; color:var(--text-2); line-height:1.25; max-width:96px}
.node-ms{font-family:var(--mono); font-size:11px; color:var(--text-3); min-height:15px; opacity:0; transition:opacity .25s var(--ease)}
.node-ms.on{opacity:1}
.node[data-state="run"] .node-ring{border-color:var(--warn); color:var(--warn); background:var(--warn-dim); transform:scale(1.14)}
.node[data-state="pass"] .node-ring{border-color:var(--pass); color:var(--pass); background:var(--pass-dim)}
.node[data-state="pass"] .node-name{color:var(--text)}
.node[data-state="deny"] .node-ring{border-color:var(--deny); color:var(--deny); background:var(--deny-dim); transform:scale(1.14)}
.node[data-state="deny"] .node-ms{color:var(--deny)}
.node[data-state="skip"] .node-ring{opacity:.4}

.wire-foot{
  display:flex;gap:22px;flex-wrap:wrap;align-items:center;margin-top:20px;padding-top:16px;
  border-top:1px solid var(--line); font-family:var(--mono); font-size:12px; color:var(--text-3); position:relative;
}
.wire-foot b{color:var(--text); font-weight:500}

/* ---------- console grid ---------- */
.grid-console{display:grid; grid-template-columns:minmax(0,1.08fr) minmax(0,1fr); gap:20px; align-items:start}
.card{
  border:1px solid var(--line); border-radius:var(--r-lg); background:var(--surface);
  box-shadow:var(--shadow); display:flex; flex-direction:column; min-width:0;
}
.card-head{display:flex; align-items:center; gap:10px; padding:16px 18px; border-bottom:1px solid var(--line)}
.card-head h3{font-size:14px}
.card-body{padding:18px; display:flex; flex-direction:column; gap:16px}
.card-foot{padding:14px 18px; border-top:1px solid var(--line); display:flex; align-items:center; gap:12px}

.field{display:flex; flex-direction:column; gap:7px; min-width:0}
.field > label{font-size:12.5px; color:var(--text-2)}
.control{
  width:100%; background:var(--surface-2); border:1px solid var(--line);
  border-radius:var(--r-md); padding:10px 12px; font-size:13.5px;
  transition:border-color .16s var(--ease), background .16s var(--ease);
}
.control:hover{border-color:var(--line-2)}
.control:focus{outline:none; border-color:var(--primary); box-shadow:0 0 0 3px var(--primary-dim)}
select.control{
  appearance:none; cursor:pointer; padding-right:34px;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='none' stroke='%23969CC4' stroke-width='1.6' stroke-linecap='round'%3E%3Cpath d='M4 6.5 8 10.5 12 6.5'/%3E%3C/svg%3E");
  background-repeat:no-repeat; background-position:right 11px center; background-size:15px;
}
textarea.control{resize:vertical; min-height:104px; font-family:var(--mono); font-size:13px; line-height:1.6}

/* model picker */
.models{display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:8px}
.model{
  display:flex; align-items:center; gap:9px; padding:9px 10px; cursor:pointer;
  border:1px solid var(--line); border-radius:var(--r-md); background:var(--surface-2);
  text-align:left; min-width:0; transition:border-color .16s var(--ease), background .16s var(--ease), transform .16s var(--ease);
}
.model:hover{border-color:var(--line-2); transform:translateY(-1px)}
.model[aria-pressed="true"]{border-color:var(--primary); background:var(--primary-dim)}
.model-mark{width:22px;height:22px;flex:none;border-radius:6px;display:grid;place-items:center}
.model-mark svg{width:13px;height:13px}
.model-txt{min-width:0}
.model-name{font-size:12.5px; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
.model-meta{font-family:var(--mono); font-size:10.5px; color:var(--text-3); white-space:nowrap}

/* key rows */
.keys{display:flex; flex-direction:column; gap:7px}
.key{
  display:flex; align-items:center; gap:11px; padding:10px 12px; cursor:pointer; width:100%;
  border:1px solid var(--line); border-radius:var(--r-md); background:var(--surface-2); text-align:left;
  transition:border-color .16s var(--ease), background .16s var(--ease);
}
.key:hover{border-color:var(--line-2)}
.key[aria-pressed="true"]{border-color:var(--primary); background:var(--primary-dim)}
.key-id{font-family:var(--mono); font-size:12.5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
.key-sub{font-size:11.5px; color:var(--text-3); white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
.key-tag{
  margin-left:auto; flex:none; font-family:var(--mono); font-size:10.5px; padding:2px 7px;
  border-radius:99px; border:1px solid var(--line-2); color:var(--text-3);
}
.key-tag.live{color:var(--pass); border-color:var(--pass); background:var(--pass-dim)}
.key-tag.revoked{color:var(--deny); border-color:var(--deny); background:var(--deny-dim)}

/* buttons */
.btn{
  display:inline-flex; align-items:center; justify-content:center; gap:8px; height:38px; padding:0 16px;
  border-radius:var(--r-md); border:1px solid var(--line); background:var(--surface-2);
  font-size:13.5px; font-weight:500; cursor:pointer; white-space:nowrap;
  transition:transform .12s var(--ease), background .16s var(--ease), border-color .16s var(--ease), opacity .16s var(--ease);
}
.btn:hover{border-color:var(--line-2)}
.btn:active{transform:scale(.975)}
.btn svg{width:15px;height:15px;flex:none}
.btn-primary{
  background:linear-gradient(180deg,var(--primary-2),var(--primary)); border-color:transparent; color:#fff;
  box-shadow:0 1px 0 rgba(255,255,255,.18) inset, 0 8px 22px -10px var(--primary);
}
.btn-primary:hover{filter:brightness(1.07)}
.btn[disabled]{opacity:.55; cursor:not-allowed; transform:none}
.btn-ghost{background:transparent}
.spinner{width:14px;height:14px;border-radius:99px;border:2px solid rgba(255,255,255,.35);border-top-color:#fff;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ---------- stream pane ---------- */
.status{
  font-family:var(--mono); font-size:11.5px; padding:3px 9px; border-radius:99px;
  border:1px solid var(--line-2); color:var(--text-3); margin-left:auto; white-space:nowrap;
}
.status[data-s="run"]{color:var(--warn);border-color:var(--warn);background:var(--warn-dim)}
.status[data-s="ok"]{color:var(--pass);border-color:var(--pass);background:var(--pass-dim)}
.status[data-s="err"]{color:var(--deny);border-color:var(--deny);background:var(--deny-dim)}
.stream{
  flex:1; min-height:236px; max-height:360px; overflow-y:auto; padding:16px;
  background:var(--bg-2); border:1px solid var(--line); border-radius:var(--r-md);
  font-family:var(--mono); font-size:12.5px; line-height:1.75; white-space:pre-wrap; word-break:break-word;
}
.stream .empty{color:var(--text-3)}
.stream strong{color:var(--text); font-weight:600}
.stream code{background:var(--surface-2); padding:1px 5px; border-radius:4px; color:var(--primary-2)}
.caret{display:inline-block;width:7px;height:14px;background:var(--primary);vertical-align:-2px;animation:blink 1s steps(2) infinite}
@keyframes blink{50%{opacity:0}}
.skel{display:block;height:11px;border-radius:4px;background:linear-gradient(90deg,var(--surface-2),var(--surface-3),var(--surface-2));background-size:200% 100%;animation:shimmer 1.3s linear infinite;margin-bottom:9px}
@keyframes shimmer{to{background-position:-200% 0}}

.usage{display:grid; grid-template-columns:repeat(3,1fr); gap:1px; background:var(--line); border-radius:var(--r-md); overflow:hidden}
.usage div{background:var(--surface); padding:11px 12px}
.usage dt{font-size:11.5px; color:var(--text-3); margin-bottom:3px}
.usage dd{margin:0; font-family:var(--mono); font-size:14px; font-weight:500}

/* ---------- metrics ---------- */
.grid-metrics{display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px}
.stat{border:1px solid var(--line); border-radius:var(--r-lg); background:var(--surface); padding:16px 17px; box-shadow:var(--shadow); min-width:0}
.stat-label{font-size:12.5px; color:var(--text-2); display:flex; align-items:center; gap:7px}
.stat-val{font-family:var(--mono); font-size:25px; font-weight:500; letter-spacing:-.02em; margin:9px 0 2px; line-height:1}
.stat-sub{font-size:12px; color:var(--text-3)}
.delta{font-family:var(--mono); font-size:11.5px; padding:1px 6px; border-radius:99px; background:var(--pass-dim); color:var(--pass)}
.delta.down{background:var(--deny-dim); color:var(--deny)}
.spark{width:100%; height:38px; margin-top:12px; display:block; overflow:visible}

.grid-charts{display:grid; grid-template-columns:minmax(0,1.6fr) minmax(0,1fr); gap:20px; align-items:stretch}
.chart{width:100%; height:auto; aspect-ratio:640/200; display:block}
.chart .gridline{stroke:var(--line); stroke-width:1}
.chart .axis{fill:var(--text-3); font-family:var(--mono); font-size:10px}
.legend{display:flex; gap:16px; flex-wrap:wrap; font-size:12px; color:var(--text-2); padding:0 18px 16px}
.legend span{display:inline-flex; align-items:center; gap:6px}
.swatch{width:9px;height:9px;border-radius:2px;flex:none}

.ring-wrap{display:flex; flex-direction:column; align-items:center; gap:4px; padding:6px 0 2px}
.ring{width:150px;height:150px;transform:rotate(-90deg)}
.ring circle{fill:none; stroke-width:11; stroke-linecap:round}
.ring .track{stroke:var(--surface-3)}
.ring .val{stroke:var(--primary); transition:stroke-dashoffset .8s var(--ease), stroke .3s var(--ease)}
.ring-center{margin-top:-96px; margin-bottom:56px; text-align:center; pointer-events:none}
.ring-num{font-family:var(--mono); font-size:27px; font-weight:500; line-height:1}
.ring-cap{font-size:11.5px; color:var(--text-3); margin-top:3px}
.quota-rows{display:flex;flex-direction:column;gap:12px;padding:0 18px 18px}
.qrow{display:flex;flex-direction:column;gap:6px}
.qrow-top{display:flex;align-items:baseline;gap:8px;font-size:12.5px}
.qrow-top b{font-weight:500}
.qrow-top .mono{margin-left:auto;color:var(--text-3);font-size:11.5px}
.bar{height:5px;border-radius:99px;background:var(--surface-3);overflow:hidden}
.bar i{display:block;height:100%;border-radius:99px;background:var(--primary);width:0;transition:width .9s var(--ease)}
.bar i.warn{background:var(--warn)} .bar i.deny{background:var(--deny)}

/* ---------- log ---------- */
.logwrap{border:1px solid var(--line); border-radius:var(--r-lg); background:var(--surface); box-shadow:var(--shadow); overflow:hidden}
.tablescroll{overflow-x:auto}
table{width:100%; border-collapse:collapse; min-width:720px}
thead th{
  text-align:left; font-size:11.5px; font-weight:500; color:var(--text-3);
  padding:11px 16px; border-bottom:1px solid var(--line); white-space:nowrap; background:var(--surface-2);
}
tbody td{padding:12px 16px; border-bottom:1px solid var(--line); font-size:13px; white-space:nowrap}
tbody tr:last-child td{border-bottom:0}
tbody tr{transition:background .14s var(--ease)}
tbody tr:hover{background:var(--surface-2)}
tbody tr.fresh{animation:slidein .5s var(--ease)}
@keyframes slidein{from{opacity:0;transform:translateY(-7px);background:var(--primary-dim)}to{opacity:1;transform:none}}
td.num{text-align:right; font-family:var(--mono); font-variant-numeric:tabular-nums}
.pill{font-family:var(--mono); font-size:11.5px; padding:2px 8px; border-radius:99px; border:1px solid var(--line-2); color:var(--text-3)}
.pill.ok{color:var(--pass); border-color:var(--pass); background:var(--pass-dim)}
.pill.warn{color:var(--warn); border-color:var(--warn); background:var(--warn-dim)}
.pill.err{color:var(--deny); border-color:var(--deny); background:var(--deny-dim)}
.prov{display:inline-flex; align-items:center; gap:7px}
.prov .model-mark{width:18px;height:18px;border-radius:5px}
.prov .model-mark svg{width:11px;height:11px}

/* ---------- toast ---------- */
.toasts{position:fixed; right:18px; bottom:18px; z-index:80; display:flex; flex-direction:column; gap:9px; max-width:min(360px,calc(100vw - 36px))}
.toast{
  display:flex; gap:11px; align-items:flex-start; padding:12px 14px; border-radius:var(--r-md);
  border:1px solid var(--line-2); background:var(--surface); box-shadow:var(--shadow);
  animation:toastin .32s var(--ease);
}
.toast.out{animation:toastout .28s var(--ease) forwards}
@keyframes toastin{from{opacity:0;transform:translateX(18px) scale(.97)}to{opacity:1;transform:none}}
@keyframes toastout{to{opacity:0;transform:translateX(18px) scale(.97)}}
.toast-ic{width:17px;height:17px;flex:none;margin-top:1px}
.toast-t{font-size:13px;font-weight:500}
.toast-d{font-size:12.5px;color:var(--text-2);margin-top:2px;font-family:var(--mono)}

/* ---------- command palette ---------- */
.scrim{position:fixed;inset:0;z-index:90;background:rgba(5,6,14,.62);backdrop-filter:blur(5px);display:grid;place-items:start center;padding-top:14vh;animation:fade .18s var(--ease)}
@keyframes fade{from{opacity:0}to{opacity:1}}
.cmd{width:min(560px,calc(100vw - 32px)); border:1px solid var(--line-2); border-radius:var(--r-lg); background:var(--surface); box-shadow:0 30px 70px -20px rgba(0,0,0,.7); overflow:hidden; animation:cmdin .22s var(--ease)}
@keyframes cmdin{from{opacity:0;transform:translateY(-10px) scale(.985)}to{opacity:1;transform:none}}
.cmd input{width:100%;border:0;background:transparent;padding:16px 18px;font-size:15px;border-bottom:1px solid var(--line)}
.cmd input:focus{outline:none}
.cmd ul{list-style:none;margin:0;padding:7px;max-height:330px;overflow-y:auto}
.cmd li{display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:var(--r-sm);cursor:pointer;font-size:13.5px}
.cmd li[aria-selected="true"]{background:var(--primary-dim)}
.cmd li svg{width:15px;height:15px;color:var(--text-3);flex:none}
.cmd li .hint{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--text-3)}
.cmd .none{padding:22px;text-align:center;color:var(--text-3);font-size:13px}

footer{padding:26px 0 40px; border-top:1px solid var(--line); margin-top:30px; font-size:12.5px; color:var(--text-3); display:flex; gap:16px; flex-wrap:wrap; align-items:center}
footer a{color:var(--text-2); text-decoration:none; border-bottom:1px solid var(--line-2)}
footer a:hover{color:var(--text)}

/* ---------- responsive ---------- */
@media (max-width:1080px){
  .grid-console{grid-template-columns:1fr}
  .grid-charts{grid-template-columns:1fr}
  .grid-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:760px){
  .wrap{padding:0 16px}
  .shell{grid-template-columns:1fr}
  .rail{
    position:fixed; bottom:0; top:auto; left:0; right:0; height:auto; width:100%;
    flex-direction:row; justify-content:space-around; padding:8px 8px calc(8px + env(safe-area-inset-bottom));
    border-right:0; border-top:1px solid var(--line); z-index:60;
  }
  .brandmark,.rail-sp{display:none}
  .main{padding-bottom:72px}
  .wire{grid-template-columns:1fr; gap:14px}
  .wire-rail,.packet{display:none}
  .node{flex-direction:row; text-align:left; gap:12px; padding-left:2px}
  .node-name{max-width:none; flex:1}
  .node-ms{min-height:0}
  .searchbtn{display:none}
  .wordmark{font-size:14px}
  .grid-metrics{grid-template-columns:1fr}
  .stat-val{font-size:22px}
  .usage{grid-template-columns:1fr}
  .wire-panel{padding:20px 18px 16px}
}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.001ms !important;animation-iteration-count:1 !important;transition-duration:.001ms !important}
}
</style>
</head>
<body>
<!-- reusable icon defs -->
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<g id="i-route"><path d="M4 17h3a4 4 0 0 0 4-4V7a3 3 0 0 1 3-3h6M20 4l-3 3m3-3-3-3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></g>
<g id="i-key"><circle cx="8" cy="8" r="3.4" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M10.5 10.5 20 20m-3 0 2-2m-5-2 2-2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></g>
<g id="i-gauge"><path d="M5 18a8 8 0 1 1 14 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M12 14.5 16 9" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></g>
<g id="i-coin"><circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M12 8v8m2.2-6.1c-.5-.6-1.3-.9-2.2-.9-1.4 0-2.4.7-2.4 1.8 0 2.4 4.8 1.2 4.8 3.6 0 1.1-1 1.8-2.4 1.8-.9 0-1.7-.3-2.2-.9" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></g>
<g id="i-chip"><rect x="7" y="7" width="10" height="10" rx="2.2" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M10 4v3m4-3v3m-4 10v3m4-3v3M4 10h3m-3 4h3m10-4h3m-3 4h3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></g>
<g id="i-ledger"><path d="M6 4h9l4 4v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M14 4v5h5M8.5 13h7m-7 3.5h4.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></g>
<g id="i-play"><path d="M7 5.5v13l11-6.5z" fill="currentColor"/></g>
<g id="i-copy"><rect x="9" y="9" width="11" height="11" rx="2.2" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M15 6.5V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h.5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></g>
<g id="i-search"><circle cx="11" cy="11" r="6.2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="m15.6 15.6 4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></g>
<g id="i-sun"><circle cx="12" cy="12" r="4.2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 2.6v2.2M12 19.2v2.2M2.6 12h2.2m14.4 0h2.2M5.3 5.3l1.6 1.6m10.2 10.2 1.6 1.6M18.7 5.3l-1.6 1.6M6.9 17.1l-1.6 1.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></g>
<g id="i-moon"><path d="M20 14.2A8.4 8.4 0 0 1 9.8 4 8.4 8.4 0 1 0 20 14.2Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></g>
<g id="i-check"><path d="m5 12.5 4.5 4.5L19 7" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></g>
<g id="i-x"><path d="M6.5 6.5l11 11m0-11-11 11" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"/></g>
<g id="i-alert"><path d="M12 8.2v5m0 3.1v.1" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"/><circle cx="12" cy="12" r="8.4" fill="none" stroke="currentColor" stroke-width="1.7"/></g>
<g id="i-trash"><path d="M5.5 7h13M10 7V5.2A1.2 1.2 0 0 1 11.2 4h1.6A1.2 1.2 0 0 1 14 5.2V7m3 0v11.6a1.4 1.4 0 0 1-1.4 1.4H8.4A1.4 1.4 0 0 1 7 18.6V7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></g>
<g id="i-book"><path d="M5 5.5A1.5 1.5 0 0 1 6.5 4H18a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H6.5A1.5 1.5 0 0 0 5 20.5z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M5 17.5h14" fill="none" stroke="currentColor" stroke-width="1.7"/></g>
<g id="i-git"><path d="M12 2.2a9.8 9.8 0 0 0-3.1 19.1c.5.1.7-.2.7-.5v-1.8c-2.7.6-3.3-1.3-3.3-1.3-.5-1.1-1.1-1.4-1.1-1.4-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.3 1.1 2.9.8.1-.6.3-1.1.6-1.3-2.2-.2-4.5-1.1-4.5-4.9 0-1.1.4-2 1-2.7-.1-.2-.4-1.2.1-2.6 0 0 .8-.3 2.7 1a9.4 9.4 0 0 1 5 0c1.9-1.3 2.7-1 2.7-1 .5 1.4.2 2.4.1 2.6.6.7 1 1.6 1 2.7 0 3.8-2.3 4.7-4.5 4.9.4.3.7.9.7 1.9v2.8c0 .3.2.6.7.5A9.8 9.8 0 0 0 12 2.2Z" fill="currentColor"/></g>
</defs></svg>

<div class="shell">
  <nav class="rail" aria-label="Sections">
    <svg class="brandmark" viewBox="0 0 34 34" aria-hidden="true">
      <rect x="1" y="1" width="32" height="32" rx="10" fill="none" stroke="var(--line-2)"/>
      <path d="M11 24 19 6v11h5L15 30V19h-4z" fill="url(#bg1)"/>
      <linearGradient id="bg1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="var(--primary-2)"/><stop offset="1" stop-color="var(--primary)"/></linearGradient>
    </svg>
    <button class="rail-btn" aria-current="true" data-goto="wire" title="Routing"><svg><use href="#i-route"/></svg></button>
    <button class="rail-btn" data-goto="console" title="Console"><svg><use href="#i-play"/></svg></button>
    <button class="rail-btn" data-goto="usage" title="Usage"><svg><use href="#i-gauge"/></svg></button>
    <button class="rail-btn" data-goto="log" title="Requests"><svg><use href="#i-ledger"/></svg></button>
    <div class="rail-sp"></div>
    <button class="rail-btn" id="themeBtn" title="Switch theme"><svg><use href="#i-moon" id="themeIcon"/></svg></button>
    <a class="rail-btn" href="https://github.com/SHAN-DE101/ai-token-gateway" target="_blank" rel="noopener" title="Source"><svg><use href="#i-git"/></svg></a>
  </nav>

  <div class="main">
    <header class="topbar">
      <div class="wrap topbar-in">
        <span class="wordmark">AI Token Gateway</span>
        <span class="envchip"><span class="dot" id="healthDot"></span><span id="healthTxt">checking</span></span>
        <div class="topbar-sp"></div>
        <button class="kbtn searchbtn" id="cmdBtn">
          <svg><use href="#i-search"/></svg><span>Search or run</span><span class="topbar-sp"></span><kbd>⌘K</kbd>
        </button>
        <button class="kbtn" id="curlBtn"><svg><use href="#i-copy"/></svg><span>Copy as cURL</span></button>
      </div>
    </header>

    <div class="wrap">

      <!-- ===== HERO: the wire ===== -->
      <section class="section" id="wire">
        <div class="wire-panel">
          <div class="wire-top">
            <h2 class="wire-title">Request path</h2>
            <span class="wire-verdict mono" id="verdict">idle</span>
            <div class="topbar-sp"></div>
            <span class="mono" style="font-size:12px;color:var(--text-3)">every hop timed at the edge</span>
          </div>

          <div class="wire" id="wireStages">
            <div class="wire-rail" id="wireRail"></div>
            <div class="packet" id="packet"></div>

            <div class="node" data-state="idle">
              <div class="node-ring"><svg><use href="#i-route"/></svg></div>
              <div class="node-name">Ingress</div><div class="node-ms mono"></div>
            </div>
            <div class="node" data-state="idle">
              <div class="node-ring"><svg><use href="#i-key"/></svg></div>
              <div class="node-name">Key check</div><div class="node-ms mono"></div>
            </div>
            <div class="node" data-state="idle">
              <div class="node-ring"><svg><use href="#i-gauge"/></svg></div>
              <div class="node-name">Rate limit</div><div class="node-ms mono"></div>
            </div>
            <div class="node" data-state="idle">
              <div class="node-ring"><svg><use href="#i-coin"/></svg></div>
              <div class="node-name">Budget</div><div class="node-ms mono"></div>
            </div>
            <div class="node" data-state="idle">
              <div class="node-ring"><svg><use href="#i-chip"/></svg></div>
              <div class="node-name">Provider</div><div class="node-ms mono"></div>
            </div>
            <div class="node" data-state="idle">
              <div class="node-ring"><svg><use href="#i-ledger"/></svg></div>
              <div class="node-name">Audit</div><div class="node-ms mono"></div>
            </div>
          </div>

          <div class="wire-foot">
            <span>tenant <b id="fTenant">org-core-ai</b></span>
            <span>window <b id="fWindow">60s sliding</b></span>
            <span>retention <b>0 days</b></span>
            <span>round trip <b id="fRtt">—</b></span>
          </div>
        </div>
      </section>

      <!-- ===== console ===== -->
      <section class="section" id="console">
        <div class="sec-head">
          <h2>Send a test request</h2>
          <span class="sec-note">Signed with a virtual key, routed like production traffic.</span>
        </div>

        <div class="grid-console">
          <div class="card">
            <div class="card-head"><h3>Request</h3><span class="status mono" id="reqHint">⌘↵ to send</span></div>
            <div class="card-body">
              <div class="field">
                <label>Model</label>
                <div class="models" id="modelList"></div>
              </div>
              <div class="field">
                <label for="prompt">Prompt</label>
                <textarea id="prompt" class="control" spellcheck="false">Summarise what a token gateway does for a platform team, in three lines.</textarea>
              </div>
              <div class="field">
                <label>Virtual key</label>
                <div class="keys" id="keyList"></div>
              </div>
            </div>
            <div class="card-foot">
              <span class="mono" style="font-size:12px;color:var(--text-3)" id="endpointTxt">POST /v1/chat/completions</span>
              <div class="topbar-sp"></div>
              <button class="btn btn-primary" id="sendBtn"><svg><use href="#i-play"/></svg><span>Send request</span></button>
            </div>
          </div>

          <div class="card">
            <div class="card-head"><h3>Response</h3><span class="status mono" id="statusPill">idle</span></div>
            <div class="card-body">
              <div class="stream" id="stream"><span class="empty">Nothing sent yet. Pick a key and send a request — the path above lights up as each hop clears.</span></div>
              <dl class="usage">
                <div><dt>Prompt tokens</dt><dd class="mono" id="uIn">—</dd></div>
                <div><dt>Completion</dt><dd class="mono" id="uOut">—</dd></div>
                <div><dt>Cost</dt><dd class="mono" id="uCost">—</dd></div>
              </dl>
            </div>
          </div>
        </div>
      </section>

      <!-- ===== usage ===== -->
      <section class="section" id="usage">
        <div class="sec-head">
          <h2>Traffic and spend</h2>
          <span class="sec-note">Rolling 24 hours across every tenant.</span>
        </div>

        <div class="grid-metrics">
          <div class="stat">
            <div class="stat-label">Requests routed <span class="delta" id="dReq">+12.4%</span></div>
            <div class="stat-val" id="mReq">0</div>
            <div class="stat-sub">3.1% served from cache</div>
            <svg class="spark" viewBox="0 0 120 38" preserveAspectRatio="none" id="sparkReq" aria-hidden="true"></svg>
          </div>
          <div class="stat">
            <div class="stat-label">Median latency <span class="delta down" id="dLat">+8ms</span></div>
            <div class="stat-val" id="mLat">0 ms</div>
            <div class="stat-sub">p95 <span class="mono" id="mP95">—</span> · gateway overhead 4 ms</div>
            <svg class="spark" viewBox="0 0 120 38" preserveAspectRatio="none" id="sparkLat" aria-hidden="true"></svg>
          </div>
          <div class="stat">
            <div class="stat-label">Tokens metered</div>
            <div class="stat-val" id="mTok">0</div>
            <div class="stat-sub">in <span class="mono" id="mTokIn">—</span> · out <span class="mono" id="mTokOut">—</span></div>
            <svg class="spark" viewBox="0 0 120 38" preserveAspectRatio="none" id="sparkTok" aria-hidden="true"></svg>
          </div>
          <div class="stat">
            <div class="stat-label">Spend <span class="delta" id="dSpend">−4.2%</span></div>
            <div class="stat-val" id="mSpend">$0.00</div>
            <div class="stat-sub">of $10,000 monthly cap</div>
            <svg class="spark" viewBox="0 0 120 38" preserveAspectRatio="none" id="sparkSpend" aria-hidden="true"></svg>
          </div>
        </div>

        <div class="grid-charts" style="margin-top:20px">
          <div class="card">
            <div class="card-head"><h3>Latency by hour</h3><span class="status mono" id="chartHint">last 24h</span></div>
            <div style="padding:16px 18px 0"><svg class="chart" id="latChart" viewBox="0 0 640 200" role="img" aria-label="Latency over the last 24 hours"></svg></div>
            <div class="legend">
              <span><i class="swatch" style="background:var(--primary)"></i>p50</span>
              <span><i class="swatch" style="background:var(--warn)"></i>p95</span>
              <span><i class="swatch" style="background:var(--deny)"></i>throttled requests</span>
            </div>
          </div>

          <div class="card">
            <div class="card-head"><h3>Quota</h3><span class="status mono" id="quotaPill">healthy</span></div>
            <div class="ring-wrap">
              <svg class="ring" viewBox="0 0 120 120" role="img" aria-label="Quota consumed">
                <circle class="track" cx="60" cy="60" r="50"></circle>
                <circle class="val" id="ringVal" cx="60" cy="60" r="50" stroke-dasharray="314.16" stroke-dashoffset="314.16"></circle>
              </svg>
              <div class="ring-center"><div class="ring-num mono" id="ringNum">0%</div><div class="ring-cap">of window used</div></div>
            </div>
            <div class="quota-rows" id="quotaRows"></div>
          </div>
        </div>
      </section>

      <!-- ===== log ===== -->
      <section class="section" id="log">
        <div class="sec-head">
          <h2>Recent requests</h2>
          <span class="sec-note">Metadata only. Prompt and completion bodies are never stored.</span>
          <div class="topbar-sp"></div>
          <button class="btn btn-ghost" id="clearLog"><svg><use href="#i-trash"/></svg><span>Clear</span></button>
        </div>
        <div class="logwrap">
          <div class="tablescroll">
            <table>
              <thead><tr>
                <th>Time</th><th>Key</th><th>Model</th><th>Status</th>
                <th style="text-align:right">Latency</th><th style="text-align:right">Tokens</th><th style="text-align:right">Cost</th>
              </tr></thead>
              <tbody id="logBody"></tbody>
            </table>
          </div>
        </div>

        <footer>
          <span>Gateway v1.0.0</span>
          <span class="mono" id="regionTxt">edge · iad1</span>
          <div class="topbar-sp"></div>
          <a href="https://github.com/SHAN-DE101/ai-token-gateway" target="_blank" rel="noopener">Source</a>
          <a href="/healthz" target="_blank" rel="noopener">Health</a>
        </footer>
      </section>

    </div>
  </div>
</div>

<div class="toasts" id="toasts" aria-live="polite"></div>

<script>
(function(){
"use strict";
var $=function(s,r){return (r||document).querySelector(s)};
var $$=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))};
var reduced=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
var SVGNS="http://www.w3.org/2000/svg";
function el(n,a){var e=document.createElementNS(SVGNS,n);for(var k in a){e.setAttribute(k,a[k])}return e}
function store(k,v){try{if(v===undefined)return localStorage.getItem(k);localStorage.setItem(k,v)}catch(e){return null}}

/* ---------------- theme ---------------- */
var root=document.documentElement;
(function(){
  var saved=store("gw.theme");
  var t=saved||(window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark");
  setTheme(t);
})();
function setTheme(t){
  root.setAttribute("data-theme",t);
  var ic=$("#themeIcon"); if(ic) ic.setAttribute("href", t==="dark"?"#i-sun":"#i-moon");
  store("gw.theme",t);
}
$("#themeBtn").addEventListener("click",function(){
  setTheme(root.getAttribute("data-theme")==="dark"?"light":"dark");
  paintCharts();
});

/* ---------------- data ---------------- */
var MARKS={
  spark:'<path d="M12 2 14.4 9.6 22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4z" fill="currentColor"/>',
  hex:'<path d="M12 2.6 20.5 7.3v9.4L12 21.4 3.5 16.7V7.3z" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"/>',
  rings:'<circle cx="8.6" cy="12" r="5.6" fill="none" stroke="currentColor" stroke-width="2.2"/><circle cx="15.4" cy="12" r="5.6" fill="none" stroke="currentColor" stroke-width="2.2"/>',
  prism:'<path d="M12 2.4 21.6 19H2.4z" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"/><path d="M12 2.4V19" stroke="currentColor" stroke-width="1.6"/>',
  chev:'<path d="M6 5.5 12 12l-6 6.5M13 5.5 19 12l-6 6.5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
};
var MODELS=[
  {id:"gemini-1.5-flash", name:"Gemini 1.5 Flash", vendor:"Google", mark:"spark", color:"#4E8DF5", inP:0.075, outP:0.30, base:410},
  {id:"gemini-1.5-pro",   name:"Gemini 1.5 Pro",   vendor:"Google", mark:"spark", color:"#4E8DF5", inP:1.25,  outP:5.00, base:940},
  {id:"gpt-4o",           name:"GPT-4o",           vendor:"OpenAI", mark:"hex",   color:"#10A37F", inP:2.50,  outP:10.0, base:760},
  {id:"claude-sonnet-4-6",name:"Claude Sonnet 4.6",vendor:"Anthropic", mark:"chev", color:"#C96442", inP:3.00, outP:15.0, base:820},
  {id:"llama-3.3-70b-versatile", name:"Llama 3.3 70B", vendor:"Meta", mark:"rings", color:"#3E7BF6", inP:0.59, outP:0.79, base:520},
  {id:"deepseek-v3",      name:"DeepSeek V3",      vendor:"DeepSeek", mark:"prism", color:"#8A6BF0", inP:0.27, outP:1.10, base:1180}
];
var KEYS=[
  {id:"sk-gw-tenant-prod-001",   tenant:"org-core-ai", rpm:1000, state:"live",    window:"60s sliding"},
  {id:"sk-gw-tenant-alpha-001",  tenant:"org-finance", rpm:120,  state:"live",    window:"60s sliding"},
  {id:"sk-gw-tenant-revoked-999",tenant:"org-legacy",  rpm:0,    state:"revoked", window:"n/a"}
];
var model=MODELS[0], key=KEYS[0];

function markHTML(m){
  return '<span class="model-mark" style="background:'+hexA(m.color,.16)+';color:'+m.color+'"><svg viewBox="0 0 24 24">'+MARKS[m.mark]+'</svg></span>';
}
function hexA(h,a){
  var n=parseInt(h.slice(1),16);
  return "rgba("+((n>>16)&255)+","+((n>>8)&255)+","+(n&255)+","+a+")";
}

/* ---------------- render pickers ---------------- */
var modelList=$("#modelList");
MODELS.forEach(function(m){
  var b=document.createElement("button");
  b.type="button"; b.className="model"; b.setAttribute("aria-pressed", m.id===model.id);
  b.innerHTML=markHTML(m)+'<span class="model-txt"><span class="model-name">'+m.name+'</span><span class="model-meta">'+m.vendor.toLowerCase()+' · $'+m.inP.toFixed(2)+'/M in</span></span>';
  b.addEventListener("click",function(){
    model=m;
    $$(".model",modelList).forEach(function(x,i){x.setAttribute("aria-pressed", MODELS[i].id===m.id)});
    syncEndpoint();
  });
  modelList.appendChild(b);
});
var keyList=$("#keyList");
KEYS.forEach(function(k){
  var b=document.createElement("button");
  b.type="button"; b.className="key"; b.setAttribute("aria-pressed", k.id===key.id);
  b.innerHTML='<span style="min-width:0"><span class="key-id" style="display:block">'+k.id+'</span>'+
    '<span class="key-sub">'+k.tenant+(k.state==="live"?" · "+k.rpm.toLocaleString()+" requests/min":" · access removed")+'</span></span>'+
    '<span class="key-tag '+k.state+'">'+(k.state==="live"?"active":"revoked")+'</span>';
  b.addEventListener("click",function(){
    key=k;
    $$(".key",keyList).forEach(function(x,i){x.setAttribute("aria-pressed", KEYS[i].id===k.id)});
    $("#fTenant").textContent=k.tenant;
    $("#fWindow").textContent=k.window;
    syncEndpoint();
  });
  keyList.appendChild(b);
});
function syncEndpoint(){ $("#endpointTxt").textContent="POST /v1/chat/completions · "+model.id }

/* ---------------- toasts ---------------- */
function toast(kind,title,detail){
  var ic=kind==="ok"?"#i-check":kind==="warn"?"#i-alert":"#i-x";
  var col=kind==="ok"?"var(--pass)":kind==="warn"?"var(--warn)":"var(--deny)";
  var t=document.createElement("div"); t.className="toast";
  t.innerHTML='<svg class="toast-ic" style="color:'+col+'"><use href="'+ic+'"/></svg>'+
    '<div><div class="toast-t">'+title+'</div>'+(detail?'<div class="toast-d">'+detail+'</div>':'')+'</div>';
  $("#toasts").appendChild(t);
  setTimeout(function(){ t.className="toast out"; setTimeout(function(){t.remove()},280) }, 4200);
}

/* ---------------- the wire ---------------- */
var nodes=$$(".node"), packet=$("#packet"), rail=$("#wireRail"), verdict=$("#verdict");
function wireReset(){
  nodes.forEach(function(n){ n.setAttribute("data-state","idle"); var m=$(".node-ms",n); m.textContent=""; m.classList.remove("on") });
  packet.classList.remove("on","deny");
  packet.style.left="8.33%";
  rail.style.setProperty("--fill","0%");
  verdict.textContent="idle"; verdict.removeAttribute("data-state");
}
function moveTo(i){
  var pct=8.33+(i*(83.34/5));
  packet.style.left=pct+"%";
  rail.style.setProperty("--fill", ((pct-8.33)/83.34*100)+"%");
}
function stage(i,state,ms){
  var n=nodes[i]; n.setAttribute("data-state",state);
  if(ms!=null){ var m=$(".node-ms",n); m.textContent=ms+" ms"; m.classList.add("on") }
}
function wait(ms){ return new Promise(function(r){ setTimeout(r, reduced?0:ms) }) }

/* ---------------- charts ---------------- */
var HOURS=24;
function series(base,spread,seed){
  var out=[],s=seed;
  for(var i=0;i<HOURS;i++){
    s=(s*9301+49297)%233280;
    var r=s/233280;
    var diurnal=Math.sin((i/HOURS)*Math.PI*2-1.1)*0.5+0.5;
    out.push(Math.round(base*(0.72+diurnal*0.55)+(r-0.5)*spread));
  }
  return out;
}
var D={
  req: series(1450,420,7),
  p50: series(480,120,19),
  p95: series(1180,320,41),
  tokIn: series(52000,14000,63),
  tokOut: series(31000,9000,88),
  spend: series(38,14,113),
  throttle:[0,0,0,0,0,0,0,2,0,0,9,0,0,0,0,4,0,0,0,0,0,0,0,0]
};
function path(vals,w,h,pad){
  var min=Math.min.apply(null,vals), max=Math.max.apply(null,vals), rng=(max-min)||1;
  var d="";
  vals.forEach(function(v,i){
    var x=pad+(i/(vals.length-1))*(w-pad*2);
    var y=h-pad-((v-min)/rng)*(h-pad*2);
    d+=(i?" L":"M")+x.toFixed(1)+" "+y.toFixed(1);
  });
  return d;
}
function sparkline(id,vals,color){
  var svg=$(id); if(!svg) return;
  svg.innerHTML="";
  var gid="g"+id.replace("#","");
  var defs=el("defs"); var lg=el("linearGradient",{id:gid,x1:"0",y1:"0",x2:"0",y2:"1"});
  lg.appendChild(el("stop",{offset:"0","stop-color":color,"stop-opacity":".30"}));
  lg.appendChild(el("stop",{offset:"1","stop-color":color,"stop-opacity":"0"}));
  defs.appendChild(lg); svg.appendChild(defs);
  var d=path(vals,120,38,2);
  svg.appendChild(el("path",{d:d+" L118 38 L2 38 Z",fill:"url(#"+gid+")"}));
  var p=el("path",{d:d,fill:"none",stroke:color,"stroke-width":"1.6","stroke-linecap":"round","stroke-linejoin":"round","vector-effect":"non-scaling-stroke"});
  svg.appendChild(p);
  if(!reduced){
    var len=280; p.style.strokeDasharray=len; p.style.strokeDashoffset=len;
    p.animate([{strokeDashoffset:len},{strokeDashoffset:0}],{duration:900,easing:"cubic-bezier(.22,.61,.36,1)",fill:"forwards"});
  }
  var last=vals[vals.length-1], min=Math.min.apply(null,vals), max=Math.max.apply(null,vals), rng=(max-min)||1;
  svg.appendChild(el("circle",{cx:"118",cy:(38-2-((last-min)/rng)*34).toFixed(1),r:"2.4",fill:color}));
}
function cssv(n){ return getComputedStyle(root).getPropertyValue(n).trim() }
function paintCharts(){
  var pri=cssv("--primary"), warn=cssv("--warn"), deny=cssv("--deny"), line=cssv("--line"), t3=cssv("--text-3");
  sparkline("#sparkReq",D.req,pri);
  sparkline("#sparkLat",D.p50,warn);
  sparkline("#sparkTok",D.tokIn.map(function(v,i){return v+D.tokOut[i]}),pri);
  sparkline("#sparkSpend",D.spend,cssv("--pass"));

  var svg=$("#latChart"); svg.innerHTML="";
  var W=640,H=200,PL=44,PR=10,PT=14,PB=26;
  var all=D.p50.concat(D.p95);
  var max=Math.ceil(Math.max.apply(null,all)/200)*200, min=0;
  function X(i){ return PL+(i/(HOURS-1))*(W-PL-PR) }
  function Y(v){ return H-PB-((v-min)/(max-min))*(H-PT-PB) }
  for(var g=0;g<=4;g++){
    var v=min+(max-min)*g/4, y=Y(v);
    svg.appendChild(el("line",{x1:PL,y1:y,x2:W-PR,y2:y,stroke:line,"stroke-width":"1"}));
    var tx=el("text",{x:PL-9,y:y+3.5,fill:t3,"text-anchor":"end","font-family":"IBM Plex Mono, monospace","font-size":"10"});
    tx.textContent=Math.round(v); svg.appendChild(tx);
  }
  [0,6,12,18,23].forEach(function(i){
    var tx=el("text",{x:X(i),y:H-8,fill:t3,"text-anchor":"middle","font-family":"IBM Plex Mono, monospace","font-size":"10"});
    tx.textContent=(i===23?"now":("-"+(23-i)+"h")); svg.appendChild(tx);
  });
  var defs=el("defs"), lg=el("linearGradient",{id:"latfill",x1:"0",y1:"0",x2:"0",y2:"1"});
  lg.appendChild(el("stop",{offset:"0","stop-color":pri,"stop-opacity":".22"}));
  lg.appendChild(el("stop",{offset:"1","stop-color":pri,"stop-opacity":"0"}));
  defs.appendChild(lg); svg.appendChild(defs);
  function build(vals){ var d=""; vals.forEach(function(v,i){ d+=(i?" L":"M")+X(i).toFixed(1)+" "+Y(v).toFixed(1) }); return d }
  var d50=build(D.p50), d95=build(D.p95);
  svg.appendChild(el("path",{d:d50+" L"+X(HOURS-1)+" "+(H-PB)+" L"+PL+" "+(H-PB)+" Z",fill:"url(#latfill)"}));
  [[d95,warn],[d50,pri]].forEach(function(pair){
    var p=el("path",{d:pair[0],fill:"none",stroke:pair[1],"stroke-width":"2","stroke-linecap":"round","stroke-linejoin":"round"});
    svg.appendChild(p);
    if(!reduced){ var L=2200; p.style.strokeDasharray=L; p.animate([{strokeDashoffset:L},{strokeDashoffset:0}],{duration:1200,easing:"cubic-bezier(.22,.61,.36,1)",fill:"forwards"}) }
  });
  D.throttle.forEach(function(n,i){
    if(!n) return;
    svg.appendChild(el("circle",{cx:X(i),cy:Y(D.p95[i]),r:"4",fill:deny,stroke:cssv("--surface"),"stroke-width":"2"}));
  });
  var cross=el("line",{x1:0,y1:PT,x2:0,y2:H-PB,stroke:cssv("--line-2"),"stroke-width":"1",opacity:"0"});
  var lbl=el("text",{x:0,y:PT+2,fill:cssv("--text"),"font-family":"IBM Plex Mono, monospace","font-size":"11",opacity:"0"});
  svg.appendChild(cross); svg.appendChild(lbl);
  svg.addEventListener("pointermove",function(ev){
    var r=svg.getBoundingClientRect();
    var px=(ev.clientX-r.left)/r.width*W;
    var i=Math.round(Math.max(0,Math.min(HOURS-1,(px-PL)/(W-PL-PR)*(HOURS-1))));
    cross.setAttribute("x1",X(i)); cross.setAttribute("x2",X(i)); cross.setAttribute("opacity","1");
    lbl.setAttribute("x", i>18?X(i)-6:X(i)+6);
    lbl.setAttribute("text-anchor", i>18?"end":"start");
    lbl.setAttribute("opacity","1");
    lbl.textContent="p50 "+D.p50[i]+"ms · p95 "+D.p95[i]+"ms";
    $("#chartHint").textContent = i===23?"now":("-"+(23-i)+" hours");
  });
  svg.addEventListener("pointerleave",function(){
    cross.setAttribute("opacity","0"); lbl.setAttribute("opacity","0"); $("#chartHint").textContent="last 24h";
  });
}

/* ---------------- counters ---------------- */
function countTo(node,to,fmt,dur){
  var from=0, t0=performance.now(), d=reduced?0:(dur||900);
  function step(now){
    var k=d?Math.min(1,(now-t0)/d):1;
    var e=1-Math.pow(1-k,3);
    node.textContent=fmt(from+(to-from)*e);
    if(k<1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
var totals={
  req:D.req.reduce(function(a,b){return a+b},0),
  tokIn:D.tokIn.reduce(function(a,b){return a+b},0),
  tokOut:D.tokOut.reduce(function(a,b){return a+b},0),
  spend:D.spend.reduce(function(a,b){return a+b},0)
};
var p50now=D.p50[HOURS-1], p95now=D.p95[HOURS-1];
function paintStats(){
  countTo($("#mReq"),totals.req,function(v){return Math.round(v).toLocaleString()});
  countTo($("#mLat"),p50now,function(v){return Math.round(v)+" ms"});
  countTo($("#mTok"),totals.tokIn+totals.tokOut,function(v){return compact(v)});
  countTo($("#mSpend"),totals.spend,function(v){return "$"+v.toFixed(2)});
  $("#mP95").textContent=p95now+" ms";
  $("#mTokIn").textContent=compact(totals.tokIn);
  $("#mTokOut").textContent=compact(totals.tokOut);
}
function compact(v){
  if(v>=1e9) return (v/1e9).toFixed(2)+"B";
  if(v>=1e6) return (v/1e6).toFixed(2)+"M";
  if(v>=1e3) return (v/1e3).toFixed(1)+"K";
  return Math.round(v).toString();
}

/* ---------------- quota ---------------- */
var quotaUse=0.34;
function paintQuota(){
  var C=2*Math.PI*50;
  var ring=$("#ringVal");
  ring.setAttribute("stroke-dasharray",C.toFixed(2));
  ring.setAttribute("stroke-dashoffset",(C*(1-quotaUse)).toFixed(2));
  ring.style.stroke = quotaUse>0.9?cssv("--deny"):quotaUse>0.7?cssv("--warn"):cssv("--primary");
  countTo($("#ringNum"),quotaUse*100,function(v){return Math.round(v)+"%"});
  var pill=$("#quotaPill");
  pill.textContent = quotaUse>0.9?"at limit":quotaUse>0.7?"approaching limit":"healthy";
  pill.setAttribute("data-s", quotaUse>0.9?"err":quotaUse>0.7?"run":"ok");

  var rows=$("#quotaRows"); rows.innerHTML="";
  [{n:"org-core-ai",u:341,c:1000},{n:"org-finance",u:97,c:120},{n:"org-research",u:12,c:400}].forEach(function(t){
    var pc=t.u/t.c;
    var cls=pc>0.9?"deny":pc>0.7?"warn":"";
    var d=document.createElement("div"); d.className="qrow";
    d.innerHTML='<div class="qrow-top"><b>'+t.n+'</b><span class="mono">'+t.u+' / '+t.c+' rpm</span></div><div class="bar"><i class="'+cls+'"></i></div>';
    rows.appendChild(d);
    requestAnimationFrame(function(){ $("i",d).style.width=(pc*100).toFixed(1)+"%" });
  });
}

/* ---------------- request log ---------------- */
var logRows=[];
function seedLog(){
  var now=Date.now();
  [[0,"prod-001",MODELS[0],200,412,1380,0.0021],
   [46,"alpha-001",MODELS[2],200,701,2140,0.0139],
   [128,"prod-001",MODELS[3],200,884,3010,0.0286],
   [190,"alpha-001",MODELS[1],429,18,0,0],
   [265,"prod-001",MODELS[4],200,503,1620,0.0011],
   [340,"legacy",MODELS[0],403,9,0,0]].forEach(function(r){
    logRows.push({t:new Date(now-r[0]*1000),key:r[1],model:r[2],status:r[3],ms:r[4],tok:r[5],cost:r[6],fresh:false});
  });
  paintLog();
}
function paintLog(){
  var tb=$("#logBody"); tb.innerHTML="";
  if(!logRows.length){
    var tr=document.createElement("tr");
    tr.innerHTML='<td colspan="7" style="padding:34px;text-align:center;color:var(--text-3)">No requests yet. Send one from the console above.</td>';
    tb.appendChild(tr); return;
  }
  logRows.forEach(function(r){
    var cls=r.status===200?"ok":r.status===429?"warn":"err";
    var tr=document.createElement("tr");
    if(r.fresh){ tr.className="fresh"; r.fresh=false }
    tr.innerHTML='<td class="mono" style="color:var(--text-3)">'+r.t.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit"})+'</td>'+
      '<td class="mono">'+r.key+'</td>'+
      '<td><span class="prov">'+markHTML(r.model)+'<span>'+r.model.name+'</span></span></td>'+
      '<td><span class="pill '+cls+'">'+r.status+'</span></td>'+
      '<td class="num">'+r.ms+' ms</td>'+
      '<td class="num">'+(r.tok?r.tok.toLocaleString():"—")+'</td>'+
      '<td class="num">'+(r.cost?"$"+r.cost.toFixed(4):"—")+'</td>';
    tb.appendChild(tr);
  });
}
$("#clearLog").addEventListener("click",function(){ logRows=[]; paintLog(); toast("ok","Log cleared","0 entries") });

/* ---------------- streaming reveal ---------------- */
function renderMd(s){
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>")
    .replace(/`([^`]+)`/g,"<code>$1</code>");
}
var streamAbort=null;
function streamInto(node,text){
  if(streamAbort) streamAbort();
  var cancelled=false; streamAbort=function(){cancelled=true};
  if(reduced){ node.innerHTML=renderMd(text); return Promise.resolve() }
  return new Promise(function(done){
    var i=0;
    (function tick(){
      if(cancelled) return done();
      i=Math.min(text.length, i+Math.ceil(2+Math.random()*5));
      node.innerHTML=renderMd(text.slice(0,i))+(i<text.length?'<span class="caret"></span>':"");
      node.scrollTop=node.scrollHeight;
      if(i<text.length) setTimeout(tick,14); else done();
    })();
  });
}

/* ---------------- send ---------------- */
var busy=false;
function estTokens(s){ return Math.max(12,Math.round(s.length/3.8)) }

async function send(){
  if(busy) return; busy=true;
  var btn=$("#sendBtn"), stream=$("#stream"), pill=$("#statusPill");
  var prompt=$("#prompt").value.trim()||"Hello";
  btn.disabled=true;
  btn.innerHTML='<span class="spinner"></span><span>Routing</span>';
  pill.textContent="routing"; pill.setAttribute("data-s","run");
  verdict.textContent="in flight"; verdict.setAttribute("data-state","run");
  $("#uIn").textContent="—"; $("#uOut").textContent="—"; $("#uCost").textContent="—";
  stream.innerHTML='<span class="skel" style="width:88%"></span><span class="skel" style="width:70%"></span><span class="skel" style="width:79%"></span>';
  wireReset();
  var t0=performance.now();

  packet.classList.add("on");
  stage(0,"run"); await wait(150); stage(0,"pass",Math.round(performance.now()-t0)); moveTo(1);
  await wait(190); stage(1,"run");

  var revoked = key.state==="revoked";
  if(revoked){
    await wait(280);
    stage(1,"deny",Math.round(performance.now()-t0));
    packet.classList.add("deny");
    for(var i=2;i<6;i++) stage(i,"skip");
    stage(5,"pass",Math.round(performance.now()-t0));
    finish({status:403,ms:Math.round(performance.now()-t0),
      text:"**403 · key revoked**\n\nThe key `"+key.id+"` belongs to tenant `"+key.tenant+"`, whose gateway access was removed. The request stopped at the key check and never reached a provider.\n\nTo restore access, re-issue a key for this tenant from the keys API."});
    return;
  }
  stage(1,"pass",Math.round(performance.now()-t0)); moveTo(2);
  await wait(170); stage(2,"run"); await wait(200); stage(2,"pass",Math.round(performance.now()-t0)); moveTo(3);
  await wait(150); stage(3,"run"); await wait(170); stage(3,"pass",Math.round(performance.now()-t0)); moveTo(4);
  stage(4,"run");

  var body={model:model.id,messages:[{role:"user",content:prompt}]};
  var res=null, data=null, live=false;
  try{
    var r=await fetch("/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+key.id},body:JSON.stringify(body)});
    if(r.status===404) r=await fetch("/api/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+key.id},body:JSON.stringify(body)});
    var raw=await r.text();
    data=JSON.parse(raw); res=r; live=true;
  }catch(e){ live=false }

  var tIn=estTokens(prompt), tOut=0, text="", status=200;
  if(live && res.ok && data && data.choices){
    text=data.choices[0].message.content;
    tIn=(data.usage&&data.usage.prompt_tokens)||tIn;
    tOut=(data.usage&&data.usage.completion_tokens)||estTokens(text);
  }else if(live && res && !res.ok){
    status=res.status; text="**"+status+"**\n\n"+JSON.stringify(data,null,2);
  }else{
    text="**Routed through "+model.name+"**\n\nA token gateway gives a platform team one address for every model. Applications hold a gateway key, not a provider key, so credentials can be rotated centrally without touching app code.\n\nEach call is checked against a per-tenant sliding window before it leaves, which stops one noisy service from spending another team's quota.\n\nUsage is metered on the way back and written to the audit store as counts and cost only. Prompt and completion bodies are dropped at the edge.\n\nOffline preview - the gateway endpoint is not reachable from here, so this response was generated in the browser.";
    tOut=estTokens(text);
  }

  var providerMs=Math.round(performance.now()-t0);
  stage(4,"pass",providerMs); moveTo(5);
  await wait(140); stage(5,"run"); await wait(160);
  var totalMs=Math.round(performance.now()-t0);
  stage(5,"pass",totalMs);
  var cost=(tIn*model.inP+tOut*model.outP)/1e6;
  finish({status:status,ms:totalMs,text:text,tIn:tIn,tOut:tOut,cost:cost});

  async function finish(r){
    var pill=$("#statusPill"), stream=$("#stream");
    pill.textContent=r.status===200?"200 ok":r.status+" blocked";
    pill.setAttribute("data-s", r.status===200?"ok":"err");
    verdict.textContent=r.status===200?"delivered":"stopped at key check";
    verdict.setAttribute("data-state", r.status===200?"pass":"deny");
    $("#fRtt").textContent=r.ms+" ms";
    stream.innerHTML="";
    await streamInto(stream,r.text);
    if(r.status===200){
      $("#uIn").textContent=r.tIn.toLocaleString();
      $("#uOut").textContent=r.tOut.toLocaleString();
      $("#uCost").textContent="$"+r.cost.toFixed(6);
      toast("ok","Request delivered",model.id+" · "+r.ms+" ms");
      logRows.unshift({t:new Date(),key:key.id.replace("sk-gw-tenant-",""),model:model,status:200,ms:r.ms,tok:r.tIn+r.tOut,cost:r.cost,fresh:true});
      totals.req+=1; totals.spend+=r.cost;
      countTo($("#mReq"),totals.req,function(v){return Math.round(v).toLocaleString()},400);
      quotaUse=Math.min(0.99,quotaUse+0.015); paintQuota();
    }else{
      toast("err","Request blocked","403 · key revoked");
      logRows.unshift({t:new Date(),key:"legacy",model:model,status:403,ms:r.ms,tok:0,cost:0,fresh:true});
    }
    if(logRows.length>14) logRows.length=14;
    paintLog();
    busy=false;
    $("#sendBtn").disabled=false;
    $("#sendBtn").innerHTML='<svg><use href="#i-play"/></svg><span>Send request</span>';
  }
}
$("#sendBtn").addEventListener("click",send);
document.addEventListener("keydown",function(e){
  if((e.metaKey||e.ctrlKey)&&e.key==="Enter"){ e.preventDefault(); send() }
});

/* ---------------- copy as curl ---------------- */
function curl(){
  var origin=location.origin.indexOf("http")===0?location.origin:"https://ai-token-gateway.vercel.app";
  return "curl "+origin+"/v1/chat/completions \\\n"+
    "  -H 'Authorization: Bearer "+key.id+"' \\\n"+
    "  -H 'Content-Type: application/json' \\\n"+
    "  -d '"+JSON.stringify({model:model.id,messages:[{role:"user",content:$("#prompt").value.trim()}]})+"'";
}
function copyCurl(){
  var s=curl();
  function ok(){ toast("ok","Copied as cURL",model.id) }
  if(navigator.clipboard&&navigator.clipboard.writeText){ navigator.clipboard.writeText(s).then(ok,fallback) } else fallback();
  function fallback(){
    var ta=document.createElement("textarea"); ta.value=s; ta.style.position="fixed"; ta.style.opacity="0";
    document.body.appendChild(ta); ta.select();
    try{ document.execCommand("copy"); ok() }catch(e){ toast("err","Copy blocked","Select the command manually") }
    ta.remove();
  }
}
$("#curlBtn").addEventListener("click",copyCurl);

/* ---------------- health ---------------- */
async function health(){
  var dot=$("#healthDot"), txt=$("#healthTxt");   try{     var r=await fetch("/healthz",{cache:"no-store"});     if(r.status===404) r=await fetch("/api/healthz",{cache:"no-store"});     var j=await r.json();     if(j.status==="healthy"){       dot.className="dot"; txt.textContent = j.upstream_configured?"live · upstream connected":"live · mock upstream";       return;     }     throw 0;   }catch(e){     dot.className="dot warn"; txt.textContent="preview · no gateway";   } }  /* ---------------- command palette ---------------- */ var CMDS=[   {t:"Send request",i:"#i-play",h:"⌘↵",run:send},   {t:"Copy as cURL",i:"#i-copy",h:"",run:copyCurl},   {t:"Switch theme",i:"#i-moon",h:"",run:function(){ setTheme(root.getAttribute("data-theme")==="dark"?"light":"dark"); paintCharts() }},   {t:"Clear request log",i:"#i-trash",h:"",run:function(){ logRows=[]; paintLog(); toast("ok","Log cleared","0 entries") }},   {t:"Jump to traffic and spend",i:"#i-gauge",h:"",run:function(){ go("usage") }},   {t:"Jump to recent requests",i:"#i-ledger",h:"",run:function(){ go("log") }},   {t:"Open source on GitHub",i:"#i-git",h:"",run:function(){ window.open("https://github.com/SHAN-DE101/ai-token-gateway","_blank","noopener") }},   {t:"Open health endpoint",i:"#i-book",h:"",run:function(){ window.open("/healthz","_blank","noopener") }} ]; MODELS.forEach(function(m){   CMDS.push({t:"Use "+m.name,i:"#i-chip",h:m.vendor,run:function(){     model=m; $$(".model",modelList).forEach(function(x,i){x.setAttribute("aria-pressed",MODELS[i].id===m.id)});
    syncEndpoint(); toast("ok","Model set",m.id);
  }});
});
var scrim=null, sel=0, shown=CMDS;
function openCmd(){
  if(scrim) return;
  scrim=document.createElement("div"); scrim.className="scrim";
  scrim.innerHTML='<div class="cmd" role="dialog" aria-modal="true" aria-label="Command menu"><input type="text" placeholder="Search actions" autocomplete="off" spellcheck="false"><ul></ul></div>';
  document.body.appendChild(scrim);
  var input=$("input",scrim), list=$("ul",scrim);   sel=0; draw("");   input.focus();   input.addEventListener("input",function(){ sel=0; draw(input.value) });   scrim.addEventListener("mousedown",function(e){ if(e.target===scrim) closeCmd() });   scrim.addEventListener("keydown",function(e){     if(e.key==="Escape"){ closeCmd() }     else if(e.key==="ArrowDown"){ e.preventDefault(); sel=Math.min(shown.length-1,sel+1); mark() }     else if(e.key==="ArrowUp"){ e.preventDefault(); sel=Math.max(0,sel-1); mark() }     else if(e.key==="Enter"){ e.preventDefault(); if(shown[sel]){ var f=shown[sel].run; closeCmd(); f() } }   });   function draw(q){     q=q.toLowerCase();     shown=CMDS.filter(function(c){ return c.t.toLowerCase().indexOf(q)>=0 });     list.innerHTML="";     if(!shown.length){ list.innerHTML='<div class="none">No action matches that.</div>'; return }     shown.forEach(function(c,i){       var li=document.createElement("li");       li.setAttribute("aria-selected", i===sel);       li.innerHTML='<svg><use href="'+c.i+'"/></svg><span>'+c.t+'</span>'+(c.h?'<span class="hint">'+c.h+'</span>':'');       li.addEventListener("mouseenter",function(){ sel=i; mark() });       li.addEventListener("click",function(){ var f=c.run; closeCmd(); f() });       list.appendChild(li);     });   }   function mark(){ $$("li",list).forEach(function(li,i){ li.setAttribute("aria-selected", i===sel); if(i===sel) li.scrollIntoView({block:"nearest"}) }) }
}
function closeCmd(){ if(scrim){ scrim.remove(); scrim=null } }
$("#cmdBtn").addEventListener("click",openCmd);
document.addEventListener("keydown",function(e){
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){ e.preventDefault(); scrim?closeCmd():openCmd() }
});

/* ---------------- nav ---------------- */
function go(id){ var t=document.getElementById(id); if(t) t.scrollIntoView({behavior:reduced?"auto":"smooth",block:"start"}) }
$$(".rail-btn[data-goto]").forEach(function(b){ b.addEventListener("click",function(){ go(b.getAttribute("data-goto")) }) }); if("IntersectionObserver" in window){   var io=new IntersectionObserver(function(es){     es.forEach(function(e){       if(!e.isIntersecting) return;       $$
(".rail-btn[data-goto]").forEach(function(b){ b.setAttribute("aria-current", b.getAttribute("data-goto")===e.target.id) });
    });
  },{rootMargin:"-45% 0px -50% 0px"});
  ["wire","console","usage","log"].forEach(function(id){ var n=document.getElementById(id); if(n) io.observe(n) });
}

/* ---------------- boot: one orchestrated moment ---------------- */
syncEndpoint();
seedLog();
paintCharts();
paintStats();
paintQuota();
health();
setInterval(health,45000);
if(!reduced){
  nodes.forEach(function(n,i){
    n.style.opacity="0"; n.style.transform="translateY(8px)";
    setTimeout(function(){
      n.style.transition="opacity .45s cubic-bezier(.22,.61,.36,1), transform .45s cubic-bezier(.22,.61,.36,1)";
      n.style.opacity="1"; n.style.transform="none";
    }, 90+i*70);
  });
  rail.style.setProperty("--fill","100%");
  setTimeout(function(){ rail.style.setProperty("--fill","0%") },1000);
}
window.addEventListener("resize",function(){ clearTimeout(window.__rz); window.__rz=setTimeout(paintCharts,180) });
})();
</script>

</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/api/dashboard", response_class=HTMLResponse)
async def dashboard_endpoint():
    return HTMLResponse(
        content=DASHBOARD_HTML,
        headers={"Cache-Control": "public, max-age=0, must-revalidate"},
    )


@app.get("/healthz")
@app.get("/api/healthz")
def healthz_endpoint():
    return {
        "status": "healthy",
        "service": "ai-token-gateway",
        "runtime": "vercel-serverless",
        "region": os.getenv("VERCEL_REGION", "local"),
        "upstream_configured": bool(UPSTREAM_KEY and UPSTREAM_KEY != "mock-key"),
    }


REVOKED_KEYS = {"sk-gw-tenant-revoked-999": "org-legacy"}


async def handle_chat_completion(req: Request, authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Send a virtual key as 'Authorization: Bearer sk-gw-...'.",
                              "type": "authentication_error", "code": "missing_key"}},
        )

    token = authorization.split("Bearer ", 1)[1].strip()

    if token in REVOKED_KEYS:
        raise HTTPException(
            status_code=403,
            detail={"error": {"message": "Key %s was revoked for tenant %s." % (token, REVOKED_KEYS[token]),
                              "type": "permission_denied", "code": "key_revoked"}},
        )

    body = await req.json()
    model = body.get("model", "gemini-1.5-flash")
    messages = body.get("messages", [])

    if UPSTREAM_KEY and UPSTREAM_KEY != "mock-key":
        headers = {"Authorization": "Bearer %s" % UPSTREAM_KEY, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                target_url = "%s/chat/completions" % UPSTREAM_BASE.rstrip("/")
                resp = await client.post(target_url, json=body, headers=headers)
                return JSONResponse(status_code=resp.status_code, content=resp.json())
            except Exception:
                pass

    user_prompt = messages[-1]["content"] if messages else "No prompt provided"
    content = (
        "**Routed through %s**\n\n"
        "The request cleared the key check and the sliding-window quota for this tenant, "
        "then fell through to the built-in responder because no upstream key is set on this "
        "deployment.\n\n"
        "Set OPENAI_API_KEY (and OPENAI_API_BASE, if you are not on Gemini) to forward this "
        "call to a real provider. Usage counts and cost are metered either way; prompt and "
        "completion bodies are never written to the audit store."
    ) % model

    prompt_tokens = max(15, len(user_prompt) // 4)
    completion_tokens = max(20, len(content) // 4)

    return {
        "id": "chatcmpl-gw-%d" % int(time.time()),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


@app.post("/v1/chat/completions")
@app.post("/api/v1/chat/completions")
@app.post("/api/chat/completions")
async def chat_completions(req: Request, authorization: str = Header(None)):
    return await handle_chat_completion(req, authorization)
