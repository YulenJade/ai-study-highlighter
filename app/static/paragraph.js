"use strict";
const $=id=>document.getElementById(id);
const dict={
 zh:{back:"← 返回原版",title:"精准段落匹配（预览版）",description:"上传文字型 PDF 和课堂笔记，定位最相关的一段原文。此版本不是 AI 语义匹配，也不保存书籍或连接 Notion。",pdfLabel:"教材 PDF（上限 15 MB）",notesLabel:"课堂笔记",analyze:"查找最相关段落",download:"下载段落高亮 PDF",resultTitle:"最相关原文",disclaimer:"结果由原文词语匹配排序，请先核对是否确实对应课堂重点。",notionTitle:"Notion 笔记同步（临时方法）",notionHelp:"复制结果并粘贴到你的 Notion 课程笔记。自动同步需要单独配置授权。",copy:"复制到 Notion",previewTitle:"高亮 PDF 预览",working:"处理中…",done:"已定位，请先检查匹配段落。",missing:"请选择 PDF 并输入课堂笔记。",large:"PDF 超过 15 MB。",nomatch:"未找到可匹配的段落。",page:"教材页码",copied:"复制成功。",pageIdLabel:"Notion 目标页面 ID（需要服务端已授权）",bookTitleLabel:"教材名称",confirmLabel:"我已核对原文，并同意将该段落写入指定 Notion 页面",publish:"写入 Notion 页面",publishHelp:"仅适用于已配置 Notion 集成的单用户演示服务；请勿在此填写集成密钥。",published:"已写入 Notion 页面。",invalidPage:"请输入有效的 Notion 页面 ID，并确认匹配结果。"},
 en:{back:"← Original tool",title:"Best paragraph match (preview)",description:"Upload a text-based PDF and class notes. This is lexical matching, not semantic AI; books are not saved and Notion is not connected yet.",pdfLabel:"Textbook PDF (max 15 MB)",notesLabel:"Class notes",analyze:"Find best paragraph",download:"Download highlighted PDF",resultTitle:"Best source paragraph",disclaimer:"This ranking uses lexical overlap. Check the passage before using it as your study highlight.",notionTitle:"Notion notes (manual export)",notionHelp:"Copy the result into your Notion course notes. Automatic sync requires OAuth configuration.",copy:"Copy for Notion",previewTitle:"Highlighted PDF preview",working:"Processing…",done:"Match ready; verify the paragraph.",missing:"Choose a PDF and enter your notes.",large:"PDF exceeds 15 MB.",nomatch:"No matching paragraph found.",page:"Book page",copied:"Copied.",pageIdLabel:"Target Notion page ID (server authorization required)",bookTitleLabel:"Book title",confirmLabel:"I verified the source passage and consent to append it to this Notion page",publish:"Publish to Notion",publishHelp:"Single-operator demo only. Configure the integration on the server; never enter the integration secret here.",published:"Published to Notion.",invalidPage:"Enter a valid Notion page ID and confirm the match."}
};
let lang="zh",best=null,url=null;
function t(k){return dict[lang][k];}
function translate(){document.documentElement.lang=lang==="zh"?"zh-CN":"en";for(const k of Object.keys(dict.zh)){if($(k))$(k).textContent=t(k);}if(best)render(best);}
function validate(){const f=$("pdf").files[0];$("error").textContent="";if(!f||!$("notes").value.trim()){$("error").textContent=t("missing");return false;}if(f.size>15*1024*1024){$("error").textContent=t("large");return false;}return true;}
function payload(){const d=new FormData();d.append("pdf",$("pdf").files[0]);d.append("notes",$("notes").value);return d;}
async function send(path){const r=await fetch(path,{method:"POST",body:payload()});if(!r.ok){let detail="HTTP "+r.status;try{detail=(await r.json()).detail||detail;}catch{}throw Error(detail);}return r;}
function updatePublish(){const id=$("pageId").value.replace(/-/g,"");$("publish").disabled=!(best?.best_match && $("confirm").checked && /^[0-9a-fA-F]{32}$/.test(id));}
function render(data){$("results").hidden=false;$("matched").textContent=data.best_match?data.best_match.text:t("nomatch");$("pageInfo").textContent=data.best_match?t("page")+": "+data.best_match.page:"";$("download").disabled=!data.best_match;updatePublish();}
function reset(){best=null;$("confirm").checked=false;updatePublish();$("results").hidden=true;$("download").disabled=true;$("status").textContent="";$("error").textContent="";$("previewCard").hidden=true;if(url){URL.revokeObjectURL(url);url=null;}}
$("lang").addEventListener("change",e=>{lang=e.target.value;translate();});
$("pdf").addEventListener("change",reset);$("notes").addEventListener("input",reset);
$("analyze").addEventListener("click",async()=>{if(!validate())return;$("analyze").disabled=true;$("download").disabled=true;$("status").textContent=t("working");try{best=await(await send("/paragraph/preview")).json();render(best);$("status").textContent=t("done");}catch(e){$("error").textContent=e.message;}finally{$("analyze").disabled=false;}});
$("download").addEventListener("click",async()=>{if(!validate()||!best?.best_match)return;$("download").disabled=true;try{const blob=await(await send("/paragraph/highlight")).blob();if(url)URL.revokeObjectURL(url);url=URL.createObjectURL(blob);$("preview").src=url;$("previewCard").hidden=false;const a=document.createElement("a");a.href=url;a.download="paragraph-highlighted.pdf";a.click();}catch(e){$("error").textContent=e.message;}finally{$("download").disabled=false;}});
$("copy").addEventListener("click",()=>{if(!best?.best_match)return;const b=best.best_match;const value=(lang==="zh"?"教材重点":"Textbook highlight")+"\n"+t("page")+": "+b.page+"\n"+b.text+"\n";navigator.clipboard.writeText(value).then(()=>{$("status").textContent=t("copied");}).catch(()=>{$("error").textContent="Clipboard permission denied";});});
$("pageId").addEventListener("input",updatePublish);
$("confirm").addEventListener("change",updatePublish);
$("publish").addEventListener("click",async()=>{
 if(!validate()||!best?.best_match||!$("confirm").checked)return;
 const id=$("pageId").value.replace(/-/g,"");
 if(!/^[0-9a-fA-F]{32}$/.test(id)){$("error").textContent=t("invalidPage");return;}
 const data=payload();data.append("page_id",id);data.append("book_title",$("bookTitle").value.trim()||"Textbook");
 $("publish").disabled=true;$("error").textContent="";$("status").textContent=t("working");
 try{const r=await fetch("/notion/publish",{method:"POST",body:data});if(!r.ok){let detail="HTTP "+r.status;try{detail=(await r.json()).detail||detail;}catch{}throw Error(detail);}$("status").textContent=t("published");$("confirm").checked=false;}
 catch(e){$("error").textContent=e.message;}finally{updatePublish();}
});
window.addEventListener("beforeunload",()=>{if(url)URL.revokeObjectURL(url);});translate();
let multiReady=false;
let multiSnapshot=null;
function selectedBatch(){return [...document.querySelectorAll(".batchChoice:checked")].map(el=>Number(el.value));}
function updateBatch(){const id=$("batchPageId").value.replace(/-/g,"");$("batchPublish").disabled=!(multiSnapshot&&selectedBatch().length>0&&selectedBatch().length<=30&&$("batchConfirm").checked&&/^[0-9a-fA-F]{32}$/.test(id));}
$("batchPageId").addEventListener("input",updateBatch);
$("batchConfirm").addEventListener("change",updateBatch);
function resetMulti(){multiSnapshot=null;$("batchControls").hidden=true;$("batchConfirm").checked=false;updateBatch();multiReady=false;$("multiDownload").disabled=true;$("multiResults").textContent="";}
$("pdf").addEventListener("change",resetMulti);
$("notes").addEventListener("input",resetMulti);
$("multiAnalyze").addEventListener("click",async()=>{
 if(!validate()){$("multiResults").textContent=$("error").textContent;$("multiResults").scrollIntoView({behavior:"smooth",block:"nearest"});return;}
 $("multiAnalyze").disabled=true;$("multiDownload").disabled=true;$("multiResults").textContent=t("working");
 try{
  const result=await(await send("/multi/preview")).json();
  multiReady=result.match_count>0;
  $("multiDownload").disabled=!multiReady;
  multiSnapshot=result;
  const holder=$("multiResults");holder.replaceChildren();
  result.results.forEach((r,i)=>{
    const row=document.createElement("div");row.style.cssText="padding:12px;margin:10px 0;border:1px solid #dae2eb;border-radius:10px";
    if(r.matched){
      const label=document.createElement("label");label.style.fontWeight="normal";
      const cb=document.createElement("input");cb.type="checkbox";cb.className="batchChoice";cb.value=String(i);cb.style.width="auto";
      cb.addEventListener("change",updateBatch);label.append(cb,document.createTextNode(" "+(lang==="zh"?"已核对并选择":"Verified and selected")));row.append(label);
    }
    const info=document.createElement("pre");
    info.textContent=(r.matched?"✓ "+t("page")+" "+r.page+" · "+r.category+" · "+r.score:"✕ 未匹配 / Unmatched")+"\\n"+r.note+(r.matched?"\\n"+r.text:"");
    row.append(info);holder.append(row);
  });
  $("batchControls").hidden=result.match_count===0;updateBatch();
 }catch(e){$("multiResults").textContent="分析失败 / Analysis failed: "+e.message;}
 finally{$("multiAnalyze").disabled=false;}
});
$("multiDownload").addEventListener("click",async()=>{
 if(!multiReady||!validate())return;
 $("multiDownload").disabled=true;
 try{
  const blob=await(await send("/multi/highlight")).blob();
  const link=URL.createObjectURL(blob);
  const a=document.createElement("a");a.href=link;a.download="multi-highlighted.pdf";a.click();
  $("preview").src=link;$("previewCard").hidden=false;
  if(url)URL.revokeObjectURL(url);url=link;
 }catch(e){$("multiResults").textContent=e.message;}
 finally{$("multiDownload").disabled=false;}
});

$("batchPublish").addEventListener("click",async()=>{
 if(!multiSnapshot||!validate())return;
 const indices=selectedBatch();if(!indices.length||indices.length>30||!$("batchConfirm").checked)return;
 const id=$("batchPageId").value.replace(/-/g,"");
 if(!/^[0-9a-fA-F]{32}$/.test(id))return;
 $("batchPublish").disabled=true;$("batchStatus").textContent=t("working");
 const data=payload();data.append("page_id",id);data.append("book_title",$("batchBook").value.trim()||"Textbook");
 data.append("selected_indices",JSON.stringify(indices));data.append("confirmed","true");
 try{
  const r=await fetch("/multi/notion/publish",{method:"POST",body:data});
  if(!r.ok){let detail="HTTP "+r.status;try{detail=(await r.json()).detail||detail;}catch{}throw Error(detail);}
  const result=await r.json();$("batchStatus").textContent=(lang==="zh"?"成功写入 ":"Published ")+result.highlights_added+(lang==="zh"?" 条重点":" highlights");
  $("batchConfirm").checked=false;document.querySelectorAll(".batchChoice").forEach(c=>c.checked=false);
 }catch(e){$("batchStatus").textContent="Notion: "+e.message;}finally{updateBatch();}
});

let cropUrl=null,cropGeneration=0;
function resetCrops(){cropGeneration++;$("cropCandidates").replaceChildren();$("cropPreview").replaceChildren();$("cropStatus").textContent="";if(cropUrl){URL.revokeObjectURL(cropUrl);cropUrl=null;}}
$("pdf").addEventListener("change",resetCrops);
$("notes").addEventListener("input",resetCrops);
$("cropAnalyze").addEventListener("click",async()=>{
 if(!validate()){$("cropStatus").textContent=$("error").textContent;return;}
 resetCrops();const generation=cropGeneration;$("cropAnalyze").disabled=true;$("cropStatus").textContent="正在查找原文候选…";
 try{
  const response=await fetch("/v07a/candidates",{method:"POST",body:payload()});
  if(!response.ok)throw Error("查找失败 HTTP "+response.status);
  const result=await response.json();if(generation!==cropGeneration)return;
  $("cropStatus").textContent="找到 "+result.candidates.length+" 个候选。词语匹配结果仅供人工核对。";
  result.candidates.forEach((c,i)=>{
   const btn=document.createElement("button");btn.textContent="查看第 "+c.page+" 页候选 "+(i+1)+" 的截图";
   btn.addEventListener("click",async()=>{
    const form=payload();form.append("candidate_index",String(i));btn.disabled=true;
    try{
     const r=await fetch("/v07a/crop",{method:"POST",body:form});
     if(!r.ok)throw Error("截图失败 HTTP "+r.status);
     const blob=await r.blob();if(generation!==cropGeneration)return;
     if(cropUrl)URL.revokeObjectURL(cropUrl);cropUrl=URL.createObjectURL(blob);
     const img=document.createElement("img");img.src=cropUrl;img.alt="教材第 "+c.page+" 页的实际 PDF 段落截图";img.style.cssText="max-width:100%;height:auto;border:1px solid #dae2eb;border-radius:8px";
     const title=document.createElement("p");title.textContent="PDF 第 "+c.page+" 页 · 词语匹配分数 "+c.score+" · 请人工核对";
     const link=document.createElement("a");link.href=cropUrl;link.download="textbook-page-"+c.page+"-crop.png";link.textContent="下载截图 PNG";
     $("cropPreview").replaceChildren(title,img,link);
    }catch(e){$("cropStatus").textContent=e.message;}finally{btn.disabled=false;}
   });$("cropCandidates").append(btn);
  });
 }catch(e){if(generation===cropGeneration)$("cropStatus").textContent=e.message;}
 finally{$("cropAnalyze").disabled=false;}
});

$("discoverNotes").addEventListener("click",async()=>{
 const btn=$("discoverNotes"),holder=$("discoveredNotes");
 btn.disabled=true;holder.replaceChildren();$("discoverStatus").textContent="正在读取已授权的课程页面…";
 try{
  const r=await fetch("/v07a/notion/discover");
  if(!r.ok){let msg="HTTP "+r.status;try{msg=(await r.json()).detail||msg;}catch{}throw Error(msg);}
  const data=await r.json();
  $("discoverStatus").textContent="已扫描 "+data.pages_scanned+" 个页面；课程候选 "+data.notes.length+" 个"+(data.incomplete?"（仅部分结果）":"")+"。请人工确认哪些是 AI 课堂笔记。";
  data.notes.forEach(item=>{
   const p=document.createElement("p"),a=document.createElement("a");
   a.href="https://www.notion.so/"+item.page_id;a.target="_blank";a.rel="noopener noreferrer";
   a.textContent=item.title||"未命名页面";
   p.append(document.createTextNode(item.course+" · "),a);
   holder.append(p);
  });
 }catch(e){$("discoverStatus").textContent="扫描失败："+e.message;}
 finally{btn.disabled=false;}
});

$("boundPreview").addEventListener("click",async()=>{
 const btn=$("boundPreview"),status=$("boundStatus"),list=$("boundCandidates"),image=$("boundImage");
 btn.disabled=true;list.replaceChildren();image.replaceChildren();status.textContent="正在从 Notion 读取课程笔记和 PDF…";
 try{
  const response=await fetch("/v07a/course/preview",{cache:"no-store"});
  if(!response.ok){let message="HTTP "+response.status;try{message=(await response.json()).detail||message;}catch{}throw Error(message);}
  const data=await response.json();
  status.textContent=data.course+" · "+data.textbook+" · PDF "+data.pdf_page_count+" 页 · 候选 "+data.candidates.length+" 个（请人工核对）";
  data.candidates.forEach((candidate,i)=>{
   const p=document.createElement("p"),b=document.createElement("button");
   b.textContent="查看第 "+candidate.page+" 页候选 "+(i+1)+" 截图";
   b.addEventListener("click",async()=>{
    b.disabled=true;image.replaceChildren();
    try{
     const r=await fetch("/v07a/course/crop/"+i,{cache:"no-store"});
     if(!r.ok)throw Error("截图接口返回 HTTP "+r.status);
     const url=URL.createObjectURL(await r.blob()),img=document.createElement("img");
     img.src=url;img.alt="PDF 第 "+candidate.page+" 页原文候选截图";img.style.maxWidth="100%";
     img.onload=()=>URL.revokeObjectURL(url);
     image.append(img);
    }catch(e){image.textContent="截图失败："+e.message;}finally{b.disabled=false;}
   });
   p.append(b,document.createTextNode(" 词语匹配分数 "+candidate.score+"；"+candidate.text.slice(0,160)));
   list.append(p);
  });
 }catch(e){status.textContent="读取失败："+e.message;}
 finally{btn.disabled=false;}
});
