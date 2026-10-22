"use strict";
const words={
zh:{title:"AI 教材划重点",subtitle:"上传可提取文字的教材 PDF，输入课堂笔记，预览匹配页码并下载彩色高亮副本。",inputTitle:"开始处理",upload:"教材 PDF（最大 15 MB）",notesLabel:"课堂笔记（每行一个原文短语）",key:"重点",definition:"定义",extra:"补充",analyze:"分析并预览",download:"下载高亮 PDF",resultsTitle:"匹配结果",empty:"上传 PDF 并点击分析，即可查看结果。",matches:"处匹配",pages:"页",previewTitle:"PDF 预览",previewHint:"下载前自动生成高亮 PDF 并在下方预览；部分移动浏览器可能只支持打开或下载。",pdfEmpty:"暂无高亮 PDF。",privacy:"本地开发版：文件提交至当前运行的后端进行处理。请勿在公开服务器上传私密教材。",working:"正在处理，请稍候…",ready:"分析完成，可以下载高亮 PDF。",downloadReady:"高亮 PDF 已生成。",missing:"请选择 PDF 并输入至少一条笔记。",tooLarge:"PDF 超过 15 MB。",pagesFound:"匹配页码",notFound:"未匹配词句",none:"无",error:"处理失败",truncated:"结果达到 1000 条上限，已截断。"},
en:{title:"AI Study Highlighter",subtitle:"Upload a text-based PDF and class notes, preview verified matches and export a color-highlighted copy.",inputTitle:"Get started",upload:"Textbook PDF (max 15 MB)",notesLabel:"Class notes (one exact phrase per line)",key:"Key point",definition:"Definition",extra:"Extra",analyze:"Analyze & preview",download:"Download highlighted PDF",resultsTitle:"Matching results",empty:"Upload a PDF and click Analyze to view matches.",matches:"matches",pages:"pages",previewTitle:"PDF preview",previewHint:"The highlighted PDF is generated for preview and download. Some mobile browsers may only open or download it.",pdfEmpty:"No highlighted PDF yet.",privacy:"Local development prototype: your file is processed by the currently running backend. Do not upload private textbooks to a public server.",working:"Processing…",ready:"Analysis complete. You can download the highlighted PDF.",downloadReady:"Highlighted PDF generated.",missing:"Choose a PDF and enter at least one note.",tooLarge:"PDF exceeds 15 MB.",pagesFound:"Matched pages",notFound:"Unmatched phrases",none:"None",error:"Processing failed",truncated:"Results capped at 1000 matches."}};
const $=id=>document.getElementById(id);
let lang="zh", lastSummary=null, lastBlob=null, objectUrl=null;
function t(k){return words[lang][k]||k;}
function translate(){
 document.documentElement.lang=lang==="zh"?"zh-CN":"en";
 document.querySelectorAll("[data-i18n]").forEach(el=>{el.textContent=t(el.dataset.i18n);});
 $("notes").placeholder=lang==="zh"?"[重点] 光合作用\n[定义] 叶绿素\n[补充] 呼吸作用":"[key] photosynthesis\n[definition] chlorophyll\n[extra] respiration";
 if(lastSummary)render(lastSummary);
}
function status(message,error=false){const el=$("status");el.textContent=message;el.className=error?"error":"ok";}
function clearPDF(){if(objectUrl){URL.revokeObjectURL(objectUrl);objectUrl=null;}$("pdfPreview").hidden=true;$("pdfPreview").removeAttribute("src");$("pdfEmpty").hidden=false;lastBlob=null;}
function reset(){lastSummary=null;$("download").disabled=true;$("summary").hidden=true;$("empty").hidden=false;clearPDF();status("");}
function render(data){
 $("summary").hidden=false;$("empty").hidden=true;
 $("matchCount").textContent=String(data.match_count);
 $("pageCount").textContent=String(data.page_count);
 $("pageList").textContent=t("pagesFound")+": "+(data.matched_pages.join(", ")||t("none"))+(data.truncated?" · "+t("truncated"):"");
 $("unmatched").textContent=t("notFound")+": "+(data.unmatched_terms.join(" · ")||t("none"));
 const ul=$("matchesList");ul.replaceChildren();
 data.matches.forEach(m=>{
  const li=document.createElement("li"),badge=document.createElement("span"),label=document.createElement("strong"),text=document.createElement("div");
  badge.className="tag "+m.category;badge.textContent=t(m.category);
  label.textContent=(lang==="zh"?"第 ":"Page ")+m.page+(lang==="zh"?" 页":"");
  text.textContent=m.text;li.append(badge,label,text);ul.append(li);
 });
}
function payload(){const data=new FormData();data.append("pdf",$("pdf").files[0]);data.append("notes",$("notes").value);return data;}
async function request(endpoint){
 const res=await fetch(endpoint,{method:"POST",body:payload()});
 if(!res.ok){let message="HTTP "+res.status;try{const data=await res.json();message=data.detail||message;}catch{}throw new Error(message);}
 return res;
}
function validate(){const file=$("pdf").files[0];if(!file||!$("notes").value.trim()){status(t("missing"),true);return false;}if(file.size>15*1024*1024){status(t("tooLarge"),true);return false;}return true;}
async function analyze(){
 if(!validate())return;
 $("analyze").disabled=true;$("download").disabled=true;clearPDF();status(t("working"));
 try{const res=await request("/preview");lastSummary=await res.json();render(lastSummary);$("download").disabled=false;status(t("ready"));}
 catch(err){lastSummary=null;$("summary").hidden=true;$("empty").hidden=false;status(t("error")+": "+err.message,true);}
 finally{$("analyze").disabled=false;}
}
async function download(){
 if(!validate()||!lastSummary)return;
 $("download").disabled=true;status(t("working"));
 try{
  const res=await request("/highlight");lastBlob=await res.blob();
  clearPDF();objectUrl=URL.createObjectURL(lastBlob);
  $("pdfPreview").src=objectUrl;$("pdfPreview").hidden=false;$("pdfEmpty").hidden=true;
  const a=document.createElement("a");a.href=objectUrl;a.download="highlighted.pdf";document.body.append(a);a.click();a.remove();
  status(t("downloadReady"));
 }catch(err){status(t("error")+": "+err.message,true);}
 finally{$("download").disabled=false;}
}
$("language").addEventListener("change",e=>{lang=e.target.value;translate();});
$("pdf").addEventListener("change",reset);
$("notes").addEventListener("input",reset);
$("analyze").addEventListener("click",analyze);
$("download").addEventListener("click",download);
window.addEventListener("beforeunload",()=>{if(objectUrl)URL.revokeObjectURL(objectUrl);});
translate();
