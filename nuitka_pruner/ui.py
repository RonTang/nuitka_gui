HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Nuitka 自动精简打包器</title>
<style>
:root{--blue:#2563d9;--blue2:#eaf1ff;--text:#202634;--muted:#7b8494;--line:#e3e8f0;--green:#16845b;--red:#d33d49;--bg:#f4f7fb}
*{box-sizing:border-box;margin:0;padding:0}html,body{height:100%;overflow:hidden}body{font:13px/1.5 "Microsoft YaHei UI","Microsoft YaHei",sans-serif;color:var(--text);background:var(--bg);display:flex;user-select:none}
aside{width:184px;flex:none;background:linear-gradient(180deg,#174faa,#2e6cdb);color:#fff;padding:22px 14px;display:flex;flex-direction:column}
.brand{padding:0 10px 24px}.brand b{font-size:17px;display:block}.brand span{font-size:11px;opacity:.7;letter-spacing:1px}
nav{display:grid;gap:8px}nav button{border:0;border-radius:9px;padding:11px 14px;text-align:left;background:transparent;color:#e5edff;font:inherit;cursor:pointer}nav button.active,nav button:hover{background:rgba(255,255,255,.16);color:#fff}nav button.active{font-weight:600}
.side-note{margin-top:auto;padding:12px 10px;font-size:11px;line-height:1.8;color:#d8e5ff;border-top:1px solid rgba(255,255,255,.16)}
.shell{min-width:0;flex:1;display:flex;flex-direction:column}header{height:44px;flex:none;background:#fff;box-shadow:inset 0 -1px 0 var(--line);display:flex;align-items:stretch;justify-content:space-between;padding:0 0 0 22px;cursor:default;user-select:none}header strong{font-size:13px;font-weight:550;display:flex;align-items:center}.win{display:flex;align-self:stretch;margin-top:1px;margin-right:1px}.win button{display:grid;place-items:center;width:46px;padding:0;border:0;border-radius:0;background:transparent;color:#566176;cursor:pointer}.win button:hover{background:#edf0f5}.win button svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}.win .close:hover{background:#d9414e;color:#fff;box-shadow:1px 0 0 #d9414e,0 -1px 0 #d9414e}.win.suppress-hover button:hover{background:transparent}.win.suppress-hover .close:hover{background:transparent;color:#566176;box-shadow:none}
main{flex:1;overflow:auto;padding:20px 24px 34px}.page{display:none;max-width:1120px;margin:auto}.page.active{display:block}.page-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.page-title h1{font-size:20px}.page-title p{color:var(--muted);font-size:12px;margin-top:3px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:17px 19px;margin-bottom:14px;box-shadow:0 2px 8px rgba(32,45,70,.025)}.card h2{font-size:14px;margin-bottom:14px}.card h2 span{font-size:11px;color:var(--muted);font-weight:400;margin-left:8px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px 16px}.grid.three{grid-template-columns:repeat(3,minmax(0,1fr))}.field{min-width:0}.field.full{grid-column:1/-1}.field label{display:block;font-size:12px;color:#596579;margin-bottom:5px}.path{display:flex;gap:7px}.path input{min-width:0;flex:1}
input[type=text],input[type=number],textarea,select{width:100%;border:1px solid #d7deea;border-radius:7px;background:#fff;color:var(--text);padding:8px 10px;font:inherit;outline:none;user-select:text}textarea{min-height:72px;resize:vertical;font-family:Consolas,monospace;font-size:12px}input:focus,textarea:focus,select:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(37,99,217,.1)}
.btn{border:1px solid #d6deeb;background:#fff;color:#354158;border-radius:7px;padding:7px 13px;font:inherit;cursor:pointer;white-space:nowrap}.btn:hover{background:#f3f6fb}.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}.btn.primary:hover{background:#1d53ba}.btn.danger{color:var(--red)}.btn:disabled{opacity:.45;cursor:not-allowed}.btn.small{padding:5px 10px;font-size:12px}
.radios,.checks{display:flex;gap:16px;align-items:center;min-height:36px;flex-wrap:wrap}.radios label,.checks label{display:flex;gap:6px;align-items:center;font-size:12px;cursor:pointer}.checks input,.radios input{accent-color:var(--blue)}.hint{font-size:11px;color:var(--muted);margin-top:5px}.actions{display:flex;gap:9px;align-items:center}.actions.right{justify-content:flex-end}
table{width:100%;border-collapse:collapse}th{text-align:left;color:var(--muted);font-size:11px;font-weight:500;background:#f8fafc}th,td{padding:8px 10px;border-bottom:1px solid #edf0f5;vertical-align:middle}td{font-size:12px}td input,td select{padding:5px 7px}.table-wrap{max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:8px}.empty{padding:24px;text-align:center;color:var(--muted)}
.status-grid{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:12px;margin-bottom:14px}.metric{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px}.metric span{font-size:11px;color:var(--muted);display:block}.metric b{font-size:19px;display:block;margin-top:4px}.metric b.ok{color:var(--green)}.metric b.bad{color:var(--red)}
.progress{height:7px;background:#e7ecf4;border-radius:8px;overflow:hidden;margin:8px 0 16px}.progress i{height:100%;width:0;background:linear-gradient(90deg,#2b6bdb,#61a0f7);display:block;transition:width .3s}
pre#logs{height:280px;overflow:auto;background:#152033;color:#d8e4f5;border-radius:9px;padding:13px 15px;font:11px/1.6 Consolas,monospace;white-space:pre-wrap;word-break:break-all;user-select:text}.chips{display:flex;gap:6px;flex-wrap:wrap;max-height:100px;overflow:auto}.chip{background:var(--blue2);color:#28559e;border-radius:5px;padding:3px 7px;font:11px Consolas,monospace}.ok{color:var(--green)}.bad{color:var(--red)}
.report-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.lists{max-height:230px;overflow:auto}.lists li{list-style:none;padding:5px 0;border-bottom:1px solid #eef1f5;font-family:Consolas,monospace;font-size:12px}.size-bars{display:grid;gap:12px}.bar-row{display:grid;grid-template-columns:105px 1fr 85px;gap:10px;align-items:center}.bar{height:12px;background:#edf1f7;border-radius:5px;overflow:hidden}.bar i{display:block;height:100%;background:#87a9e8}.bar.final i{background:#2d72dc}.command{white-space:pre-wrap;word-break:break-all;max-height:160px;overflow:auto;background:#f5f7fa;border-radius:8px;padding:12px;font:11px/1.7 Consolas,monospace;user-select:text}.warning{color:#9a6714;background:#fff8e7;border-radius:7px;padding:8px 10px;margin-top:8px;font-size:12px}
#toast{position:fixed;right:22px;bottom:22px;max-width:520px;background:#28364d;color:#fff;padding:10px 15px;border-radius:8px;box-shadow:0 8px 30px #0003;display:none;z-index:9}#toast.show{display:block}
@media(max-width:950px){aside{width:156px}.grid.three{grid-template-columns:1fr 1fr}.status-grid{grid-template-columns:1fr 1fr}.report-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<aside>
  <div class="brand"><b>Nuitka Pruner</b><span>DELTA DEBUGGING</span></div>
  <nav>
    <button class="active" data-page="config">配置</button>
    <button data-page="run">运行</button>
    <button data-page="report">报告</button>
  </nav>
  <div class="side-note">源码预筛 · 真实构建验证<br>状态自动保存，可断点续跑</div>
</aside>
<div class="shell">
<header><strong id="header-title">配置精简任务</strong><div class="win" id="window-controls"><button data-window-action="minimize" title="最小化" aria-label="最小化" onclick="minimizeWindow()"><svg viewBox="0 0 16 16"><path d="M3 8h10"/></svg></button><button id="maximize-button" title="最大化" aria-label="最大化" onclick="__window_toggle_maximize()"><svg viewBox="0 0 16 16"><rect x="3.5" y="3.5" width="9" height="9" rx="1"/></svg></button><button class="close" title="关闭" aria-label="关闭" onclick="__window_close()"><svg viewBox="0 0 16 16"><path d="m4 4 8 8m0-8-8 8"/></svg></button></div></header>
<main>
<section class="page active" id="page-config">
  <div class="page-title"><div><h1>配置</h1><p>迭代阶段始终使用 standalone；此处模式只影响最终交付物。</p></div><button class="btn primary" onclick="startRun()">开始精简</button></div>
  <div class="card"><h2>基本</h2><div class="grid">
    <div class="field full"><label>入口脚本</label><div class="path"><input type="text" id="entry" placeholder="main.py"><button class="btn" onclick="pickEntry()">浏览</button></div></div>
    <div class="field full"><label>输出目录</label><div class="path"><input type="text" id="output_dir"><button class="btn" onclick="pickDirectory()">浏览</button></div></div>
    <div class="field"><label>产品名称</label><input type="text" id="product_name"></div>
    <div class="field"><label>产品版本</label><input type="text" id="product_version" placeholder="1.0.0.0"></div>
    <div class="field"><label>公司</label><input type="text" id="company_name"></div>
    <div class="field"><label>图标（只用于最终产物）</label><div class="path"><input type="text" id="icon"><button class="btn small" onclick="pickIcon()">浏览</button></div></div>
    <div class="field full"><label>附加 Nuitka 参数（高级）</label><textarea id="extra_args" placeholder="每行或用空格分隔；冲突的输出与迭代参数会被过滤"></textarea></div>
  </div></div>
  <div class="card"><h2>打包与插件</h2><div class="grid">
    <div class="field"><label>最终打包模式</label><div class="radios"><label><input type="radio" name="mode" value="onefile" checked>onefile</label><label><input type="radio" name="mode" value="standalone">standalone 文件夹</label></div></div>
    <div class="field"><label>控制台</label><select id="console"><option value="disable">disable（GUI）</option><option value="attach">attach</option><option value="force">force（CLI）</option></select></div>
    <div class="field full"><label>插件（选择入口后自动预勾选）</label><div class="checks" id="plugins"><label><input type="checkbox" value="pyside6">pyside6</label><label><input type="checkbox" value="pyqt5">pyqt5</label><label><input type="checkbox" value="pyqt6">pyqt6</label><label><input type="checkbox" value="tk-inter">tk-inter</label><label><input type="checkbox" value="numpy">numpy</label></div></div>
  </div></div>
  <div class="card"><h2>数据文件 <span>目标路径使用 Nuitka 的 source=target 规则</span></h2>
    <div class="checks" style="margin-bottom:10px"><label><input type="checkbox" id="auto_data" checked>pyminiwebview 项目自动包含源码引用的 HTML / JS / CSS / 图片等资源</label></div>
    <div class="table-wrap"><table><thead><tr><th>源路径</th><th>相对目标</th><th>类型</th><th>估算体积</th><th></th></tr></thead><tbody id="data-rows"></tbody></table></div>
    <div class="actions" style="margin-top:10px"><button class="btn small" onclick="addDataRow()">添加文件</button><button class="btn small" onclick="addDataRow('dir')">添加目录</button></div>
  </div>
  <div class="card"><h2>体积优化 <span>仅最终构建启用</span></h2><div class="checks">
    <label><input type="checkbox" id="lto" checked>LTO</label><label><input type="checkbox" id="no_asserts" checked>no_asserts</label><label><input type="checkbox" id="no_docstrings" checked>no_docstrings</label><label><input type="checkbox" id="upx">UPX</label><span class="hint" id="upx-hint"></span>
  </div></div>
  <div class="card"><h2>onefile 定制 <span>仅最终 onefile 使用，迭代构建不启用</span></h2><div class="grid">
    <div class="field full"><div class="checks"><label><input type="checkbox" id="custom_onefile">使用自定义 OnefileBootstrap.c 壳并复制 python3.dll 证书表</label></div><div class="hint">通过 signed_payload_plugin.py 接入；这是复制证书表，不是对新程序重新进行 Authenticode 签名。</div></div>
    <div class="field full"><label>签名插件路径（同目录需有 OnefileBootstrap.c）</label><div class="path"><input type="text" id="signed_plugin"><button class="btn" onclick="pickSignedPlugin()">浏览</button></div></div>
    <div class="field full"><label>custom onefile bootstrap 标识</label><input type="text" id="onefile_bootstrap_name" value="custom onefile bootstrap"><div class="hint">用于自定义壳的错误弹窗标题和错误输出，支持中文。</div></div>
  </div></div>
  <div class="card"><h2>精简控制</h2><div class="grid three">
    <div class="field full"><div class="checks"><label><input type="checkbox" id="deep_review">深度复核预筛必需项（按体积降序，成功项立即排除）</label></div></div>
    <div class="field full"><div class="checks"><label><input type="checkbox" id="full_ddmin">完整 ddmin：复核全部候选，不使用预筛约束、日志剪枝或分层捷径（可能产生很多编译）</label></div></div>
    <div class="field"><label>深度复核最大编译轮数</label><input type="number" id="deep_review_attempts" value="5" min="1" max="50"></div>
    <div class="field"><label>并行 jobs</label><input type="number" id="jobs" min="1" max="256"></div>
    <div class="field"><label>单轮超时（分钟）</label><input type="number" id="timeout_minutes" value="20" min="1" max="240"></div>
    <div class="field"><label>断言串</label><input type="text" id="assertion" value="SMOKE_OK"></div>
    <div class="field full"><label>追加白名单（逗号分隔，永不排除）</label><input type="text" id="whitelist" placeholder="module_a,module_b"></div>
    <div class="field full"><div class="checks"><label><input type="checkbox" id="auto_smoke" checked>自动冒烟：检测 GUI 窗口、运行异常并正常关闭，目标无需编写 smoke-test（严格功能自检时可关闭）</label></div></div>
    <div class="field full"><label>冒烟测试命令</label><input type="text" id="smoke_command" value='"{executable}"'><div class="hint">{executable} 在源码预筛时替换为 Python，在编译验证时替换为产物；自动模式会补发断言并关闭 GUI。</div></div>
  </div></div>
  <div class="actions right"><button class="btn primary" onclick="startRun()">开始精简</button></div>
</section>
<section class="page" id="page-run">
  <div class="page-title"><div><h1>运行</h1><p>每轮结束即写入 pruner_state.json；暂停在当前进程结束后生效。</p></div><div class="actions"><button class="btn primary" id="pause-btn" onclick="pauseRun()">暂停</button><button class="btn primary" id="resume-btn" onclick="resumeRun()">继续</button><button class="btn danger" id="abort-btn" onclick="abortRun()">中止</button><button class="btn" onclick="resetRun()">重置</button></div></div>
  <div class="status-grid"><div class="metric"><span>当前阶段 / 状态</span><b id="phase">空闲</b></div><div class="metric"><span>真实编译轮次（不含缓存）</span><b id="rounds">0 / 0</b></div><div class="metric"><span>候选 / 已排除 / 必保留</span><b id="counts">0 / 0 / 0</b></div></div>
  <div class="progress"><i id="progress-bar"></i></div>
  <div class="card"><h2>本轮排除集合</h2><div class="chips" id="current-set"><span class="empty">暂无</span></div><div class="hint" id="run-error"></div></div>
  <div class="card"><h2>测试历史</h2><div class="table-wrap"><table><thead><tr><th>阶段</th><th>结果</th><th>排除数</th><th>构建 / 测试</th><th>体积</th></tr></thead><tbody id="history"></tbody></table></div></div>
  <div class="card"><h2>实时日志</h2><pre id="logs"></pre></div>
</section>
<section class="page" id="page-report">
  <div class="page-title"><div><h1>报告</h1><p>最终产物会再执行一次完整冒烟测试。</p></div><div class="actions"><button class="btn" onclick="openOutput()">打开输出目录</button><button class="btn" onclick="exportReport('json')">导出 JSON</button><button class="btn" onclick="exportReport('py')">导出 py</button><button class="btn primary" onclick="exportReport('bat')">导出 bat</button></div></div>
  <div id="report-empty" class="card empty">完成一次精简后，此处显示体积对比与最小排除清单。</div>
  <div id="report-content" style="display:none">
    <div class="status-grid"><div class="metric"><span>基线 standalone</span><b id="baseline-size">--</b></div><div class="metric"><span>最终产物</span><b id="final-size">--</b></div><div class="metric"><span>节省</span><b class="ok" id="saved">--</b></div></div>
    <div class="card"><h2>体积对比</h2><div class="size-bars"><div class="bar-row"><span>基线</span><div class="bar"><i id="baseline-bar"></i></div><b id="baseline-label"></b></div><div class="bar-row"><span>精简 standalone</span><div class="bar"><i id="standalone-bar"></i></div><b id="standalone-label"></b></div><div class="bar-row"><span>最终产物</span><div class="bar final"><i id="final-bar"></i></div><b id="final-label"></b></div></div><div class="hint" id="elapsed"></div></div>
    <div class="report-grid"><div class="card"><h2>安全排除 <span id="excluded-count"></span></h2><ul class="lists" id="excluded-list"></ul></div><div class="card"><h2>必须保留 <span id="required-count"></span></h2><ul class="lists" id="required-list"></ul></div></div>
    <div class="card"><h2>最终打包命令 <button class="btn small" style="float:right" onclick="copyCommand()">复制</button></h2><div class="command" id="command"></div><div id="warnings"></div></div>
    <div class="card"><h2>大数据目录 <span>nofollow 无法移除这些资源</span></h2><div class="table-wrap"><table><thead><tr><th>目录</th><th>体积</th><th>建议</th></tr></thead><tbody id="large-data"></tbody></table></div></div>
  </div>
</section>
</main></div>
<div id="toast"></div>
<script>
const $=id=>document.getElementById(id);let lastState=null,lastLog='',toastTimer=null,polling=false;
const PHASES={idle:'空闲',baseline:'基线',prefilter:'源码预筛',ddmin:'编译 ddmin',deep_review:'深度复核',final:'最终打包',done:'已完成'};
function toast(message,error=false){const el=$('toast');el.textContent=message;el.style.background=error?'#a92e3a':'#28364d';el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),error?6500:2600)}
function errorText(e){return e&&e.error?e.error.message:(e&&e.message?e.message:String(e))}
async function api(name,...args){return await window[name](...args)}
function setMaximized(maximized){const button=$('maximize-button');button.innerHTML=maximized?'<svg viewBox="0 0 16 16"><path d="M5 6V3.5h7.5V11H10"/><rect x="3.5" y="6" width="6.5" height="6.5" rx="1"/></svg>':'<svg viewBox="0 0 16 16"><rect x="3.5" y="3.5" width="9" height="9" rx="1"/></svg>';button.title=maximized?'还原':'最大化';button.setAttribute('aria-label',button.title)}
function minimizeWindow(){$('window-controls').classList.add('suppress-hover');__window_minimize()}
$('window-controls').addEventListener('pointerleave',()=>$('window-controls').classList.remove('suppress-hover'));
function syncPruneModes(){const full=$('full_ddmin').checked,deep=$('deep_review').checked;$('deep_review').disabled=full;$('full_ddmin').disabled=deep;$('deep_review_attempts').disabled=full}
$('full_ddmin').onchange=()=>{if($('full_ddmin').checked)$('deep_review').checked=false;syncPruneModes()};
$('deep_review').onchange=()=>{if($('deep_review').checked)$('full_ddmin').checked=false;syncPruneModes()};
function switchPage(name){document.querySelectorAll('.page').forEach(x=>x.classList.toggle('active',x.id==='page-'+name));document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('active',x.dataset.page===name));$('header-title').textContent={config:'配置精简任务',run:'运行与断点续跑',report:'精简报告'}[name];if(name==='report')refresh()}
document.querySelectorAll('nav button').forEach(x=>x.onclick=()=>switchPage(x.dataset.page));$('auto_data').onchange=()=>{if($('auto_data').checked)inspectEntry();else document.querySelectorAll('#data-rows tr[data-auto]').forEach(x=>x.remove())};document.querySelector('header').addEventListener('mousedown',e=>{if(e.button===0&&!e.target.closest('button'))__window_start_move()});
function fmtMB(bytes){return bytes?((bytes/1048576).toFixed(bytes>10485760?1:2)+' MB'):'0 MB'}
function fmtTime(seconds){seconds=Number(seconds||0);if(seconds<60)return seconds.toFixed(1)+'s';return Math.floor(seconds/60)+'m '+Math.round(seconds%60)+'s'}
function quoteCmd(s){s=String(s);return /[\s&]/.test(s)?'"'+s.replace(/"/g,'\\"')+'"':s}
async function pickEntry(){try{const path=await api('pruner_pick_file','py');if(path){$('entry').value=path;await inspectEntry()}}catch(e){toast(errorText(e),true)}}
async function inspectEntry(){try{const result=await api('pruner_inspect_entry',$('entry').value);document.querySelectorAll('#plugins input').forEach(x=>x.checked=result.plugins.includes(x.value));document.querySelectorAll('#data-rows tr[data-auto]').forEach(x=>x.remove());if($('auto_data').checked){const existing=new Set([...document.querySelectorAll('.data-source')].map(x=>x.value.toLowerCase()));result.data_items.forEach(item=>{if(!existing.has(item.source.toLowerCase()))addDataRow('file',item)})}}catch(e){toast(errorText(e),true)}}
async function pickDirectory(){try{const path=await api('pruner_pick_directory');if(path)$('output_dir').value=path}catch(e){toast(errorText(e),true)}}
async function pickIcon(){try{const path=await api('pruner_pick_file','ico');if(path)$('icon').value=path}catch(e){toast(errorText(e),true)}}
async function pickSignedPlugin(){try{const path=await api('pruner_pick_file','py');if(path)$('signed_plugin').value=path}catch(e){toast(errorText(e),true)}}
function addDataRow(kind='file',values={}){const tr=document.createElement('tr');if(values.auto)tr.dataset.auto='true';tr.innerHTML='<td><input type="text" class="data-source"></td><td><input type="text" class="data-target" placeholder="资源相对路径"></td><td><select class="data-kind"><option value="file">文件</option><option value="dir">目录</option></select></td><td class="data-size">--</td><td><button class="btn small danger">删除</button></td>';tr.querySelector('.data-kind').value=values.kind||kind;tr.querySelector('.data-source').value=values.source||'';tr.querySelector('.data-target').value=values.target||'';tr.querySelector('button').onclick=()=>tr.remove();const update=async()=>{try{const r=await api('pruner_path_size',tr.querySelector('.data-source').value);tr.querySelector('.data-size').textContent=r.exists?fmtMB(r.size_bytes):'不存在'}catch(e){}};tr.querySelector('.data-source').onchange=update;tr.querySelector('.data-kind').onchange=update;$('data-rows').appendChild(tr);if(values.source)update()}
function collectConfig(){const selected=document.querySelector('input[name=mode]:checked');return{entry:$('entry').value,output_dir:$('output_dir').value,product_name:$('product_name').value,product_version:$('product_version').value,company_name:$('company_name').value,extra_args:$('extra_args').value,mode:selected.value,console:$('console').value,icon:$('icon').value,plugins:[...document.querySelectorAll('#plugins input:checked')].map(x=>x.value),data_items:[...$('data-rows').children].map(tr=>({source:tr.querySelector('.data-source').value,target:tr.querySelector('.data-target').value,kind:tr.querySelector('.data-kind').value})).filter(x=>x.source||x.target),auto_data:$('auto_data').checked,lto:$('lto').checked,no_asserts:$('no_asserts').checked,no_docstrings:$('no_docstrings').checked,upx:$('upx').checked,whitelist:$('whitelist').value.split(/[,，\n]/).map(x=>x.trim()).filter(Boolean),deep_review:$('deep_review').checked,full_ddmin:$('full_ddmin').checked,deep_review_attempts:Number($('deep_review_attempts').value),custom_onefile:$('custom_onefile').checked,signed_plugin:$('signed_plugin').value,onefile_bootstrap_name:$('onefile_bootstrap_name').value,jobs:Number($('jobs').value),timeout_minutes:Number($('timeout_minutes').value),auto_smoke:$('auto_smoke').checked,smoke_command:$('smoke_command').value,assertion:$('assertion').value}}
async function startRun(){try{await api('pruner_start',collectConfig());switchPage('run');refresh()}catch(e){toast(errorText(e),true)}}
async function pauseRun(){try{await api('pruner_pause');refresh()}catch(e){toast(errorText(e),true)}}
async function resumeRun(){try{await api('pruner_resume');refresh()}catch(e){toast(errorText(e),true)}}
async function abortRun(){try{await api('pruner_abort');refresh()}catch(e){toast(errorText(e),true)}}
async function resetRun(){if(!confirm('清除当前状态和历史？日志文件会保留。'))return;try{await api('pruner_reset');refresh()}catch(e){toast(errorText(e),true)}}
function textRow(tbody,values,classes=[]){const tr=document.createElement('tr');values.forEach((v,i)=>{const td=document.createElement('td');td.textContent=v;if(classes[i])td.className=classes[i];tr.appendChild(td)});tbody.appendChild(tr)}
function renderHistory(history){const body=$('history');body.replaceChildren();if(!history.length){body.innerHTML='<tr><td colspan="5" class="empty">尚无测试</td></tr>';return}history.slice(-120).reverse().forEach(h=>textRow(body,[{baseline:'基线',prefilter:'预筛',ddmin:'ddmin',deep_review:'深度复核',final:'最终'}[h.kind]||h.kind,h.ok?'通过':'失败',(h.set||[]).length,fmtTime(h.build_s)+' / '+fmtTime(h.test_s),fmtMB(h.size_bytes)],['',h.ok?'ok':'bad']))}
function renderList(id,names){const list=$(id);list.replaceChildren();if(!names.length){const li=document.createElement('li');li.textContent='无';list.appendChild(li)}else names.forEach(name=>{const li=document.createElement('li');li.textContent=name;list.appendChild(li)})}
function renderReport(state){const r=state.report;if(!r||state.phase!=='done'){$('report-empty').style.display='block';$('report-content').style.display='none';return}$('report-empty').style.display='none';$('report-content').style.display='block';$('baseline-size').textContent=fmtMB(r.baseline_size_bytes);$('final-size').textContent=fmtMB(r.final_size_bytes);$('saved').textContent=fmtMB(r.saved_bytes)+' / '+r.saved_percent.toFixed(1)+'%';const max=Math.max(r.baseline_size_bytes,r.final_size_bytes,1);$('baseline-bar').style.width='100%';$('baseline-label').textContent=fmtMB(r.baseline_size_bytes);$('standalone-bar').style.width=(100*(r.pruned_standalone_size_bytes||r.baseline_size_bytes)/max)+'%';$('standalone-label').textContent=fmtMB(r.pruned_standalone_size_bytes||r.baseline_size_bytes);$('final-bar').style.width=(100*r.final_size_bytes/max)+'%';$('final-label').textContent=fmtMB(r.final_size_bytes);$('elapsed').textContent='总耗时 '+fmtTime(r.elapsed_s)+' · '+(state.config.mode==='onefile'?'最终为 onefile':'最终为 standalone')+' · '+(r.verification_mode==='full-ddmin'?'完整 ddmin':'快速分层')+' · '+(r.smoke_mode==='automatic'?'自动冒烟':'严格自定义冒烟');renderList('excluded-list',r.excluded);renderList('required-list',r.required);$('excluded-count').textContent=r.excluded.length+' 个';$('required-count').textContent=r.required.length+' 个';$('command').textContent=(r.final_command||[]).map(quoteCmd).join(' ');const warnings=$('warnings');warnings.replaceChildren();r.warnings.forEach(w=>{const d=document.createElement('div');d.className='warning';d.textContent=w;warnings.appendChild(d)});const data=$('large-data');data.replaceChildren();if(!r.large_data.length)data.innerHTML='<tr><td colspan="3" class="empty">未发现超过 1MB 的独立数据目录</td></tr>';else r.large_data.forEach(x=>textRow(data,[x.name,fmtMB(x.size_bytes),'检查 noinclude-data-files 或手工资源精简']))}
function render(state){lastState=state;let phaseText=(PHASES[state.phase]||state.phase)+' / '+state.status;if(state.phase==='ddmin'&&state.ddmin_progress&&state.ddmin_progress.size)phaseText+=' · 粒度 '+state.ddmin_progress.n+'/'+state.ddmin_progress.size;$('phase').textContent=phaseText;$('phase').className=state.status==='error'?'bad':state.phase==='done'?'ok':'';const compiled=state.history.filter(x=>x.kind==='ddmin'||x.kind==='deep_review').length;$('rounds').textContent=compiled+' 次';$('counts').textContent=state.candidates.length+' / '+state.excluded.length+' / '+state.required.length;$('pause-btn').disabled=!state.running||state.paused;$('resume-btn').disabled=state.running&&!state.paused||state.phase==='done'||!state.config;$('abort-btn').disabled=!state.running;const set=$('current-set');set.replaceChildren();if(!state.current_set.length){const s=document.createElement('span');s.className='hint';s.textContent='当前没有测试集合';set.appendChild(s)}else state.current_set.forEach(x=>{const s=document.createElement('span');s.className='chip';s.textContent=x;set.appendChild(s)});$('run-error').textContent=state.error||'';renderHistory(state.history);const total=state.candidates.length;const pending=state.prefilter_pending.length;let percent=0;if(state.phase==='baseline')percent=5;else if(state.phase==='prefilter')percent=10+35*(total-pending)/Math.max(total,1);else if(state.phase==='ddmin')percent=Math.min(78,50+compiled*2);else if(state.phase==='deep_review')percent=82+Math.min(8,state.deep_review_rounds);else if(state.phase==='final')percent=92;else if(state.phase==='done')percent=100;$('progress-bar').style.width=percent+'%';const logs=state.logs.join('\n');if(logs!==lastLog){const nearBottom=$('logs').scrollHeight-$('logs').scrollTop-$('logs').clientHeight<50;$('logs').textContent=logs;if(nearBottom)$('logs').scrollTop=$('logs').scrollHeight;lastLog=logs}renderReport(state)}
async function refresh(){if(polling)return;polling=true;try{render(await api('pruner_get_state'))}catch(e){}finally{polling=false}}
async function copyCommand(){if(!lastState||!lastState.report)return;const text=(lastState.report.final_command||[]).map(quoteCmd).join(' ');try{await navigator.clipboard.writeText(text);toast('命令已复制')}catch(e){toast('复制失败，请手动选择命令',true)}}
async function exportReport(kind){try{const path=await api('pruner_export',kind);if(path)toast('已导出：'+path)}catch(e){toast(errorText(e),true)}}
async function openOutput(){try{await api('pruner_open_output')}catch(e){toast(errorText(e),true)}}
window.onLog=()=>{};window.onPhaseChange=()=>refresh();window.onRoundDone=()=>refresh();
(async()=>{try{const d=await api('pruner_defaults');$('entry').value=d.entry;$('output_dir').value=d.output_dir;$('icon').value=d.icon;$('signed_plugin').value=d.signed_plugin;$('jobs').value=d.jobs;$('upx-hint').textContent=d.upx_available?'检测到 UPX':'未检测到 UPX（保持关闭）';syncPruneModes();await inspectEntry();await refresh()}catch(e){toast(errorText(e),true)}})();setInterval(refresh,1000);
</script>
</body></html>'''
