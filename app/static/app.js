"use strict";
const words={
zh:{title:"AI 教材划重点",subtitle:"上传可提取文字的教材 PDF，输入课堂笔记，预览匹配页码并下载彩色高亮副本。",inputTitle:"开始处理",upload:"教材 PDF / DOCX / PPTX / TXT / MD（默认最大 100 MB）",notesLabel:"课堂笔记（每行一个原文短语）",key:"重点",definition:"定义",extra:"补充",analyze:"分析并预览",download:"下载高亮 PDF",resultsTitle:"匹配结果",empty:"上传 PDF 并点击分析，即可查看结果。",matches:"处匹配",pages:"页",previewTitle:"PDF 预览",previewHint:"下载前自动生成高亮 PDF 并在下方预览；部分移动浏览器可能只支持打开或下载。",pdfEmpty:"暂无高亮 PDF。",privacy:"配置私有书库后可重复选择教材；未配置时仅临时处理。只有 PDF 支持原文件高亮，其他格式支持文字提取。",working:"正在处理，请稍候…",ready:"分析完成，可以下载高亮 PDF。",downloadReady:"高亮 PDF 已生成。",missing:"请选择 PDF 并输入至少一条笔记。",tooLarge:"PDF 超过 100 MB。",pagesFound:"匹配页码",notFound:"未匹配词句",none:"无",error:"处理失败",truncated:"结果达到 1000 条上限，已截断。"},
en:{title:"AI Study Highlighter",subtitle:"Upload a text-based PDF and class notes, preview verified matches and export a color-highlighted copy.",inputTitle:"Get started",upload:"PDF / DOCX / PPTX / TXT / MD (default max 100 MB)",notesLabel:"Class notes (one exact phrase per line)",key:"Key point",definition:"Definition",extra:"Extra",analyze:"Analyze & preview",download:"Download highlighted PDF",resultsTitle:"Matching results",empty:"Upload a PDF and click Analyze to view matches.",matches:"matches",pages:"pages",previewTitle:"PDF preview",previewHint:"The highlighted PDF is generated for preview and download. Some mobile browsers may only open or download it.",pdfEmpty:"No highlighted PDF yet.",privacy:"Configured private libraries retain books for reuse. Otherwise processing is temporary. Only PDF supports annotation; other formats support text extraction.",working:"Processing…",ready:"Analysis complete. You can download the highlighted PDF.",downloadReady:"Highlighted PDF generated.",missing:"Choose a PDF and enter at least one note.",tooLarge:"PDF exceeds 100 MB.",pagesFound:"Matched pages",notFound:"Unmatched phrases",none:"None",error:"Processing failed",truncated:"Results capped at 1000 matches."}};
const $=id=>document.getElementById(id);
let libraryEnabled=false;
let maxBookBytes=100*1024*1024;
let lang="zh", lastSummary=null, lastBlob=null, objectUrl=null;
function t(k){return words[lang][k]||k;}
function translate(){
 $("modeBadge").textContent="V0.4 · "+(libraryEnabled?(lang==="zh"?"私有持久书库":"Persistent private library"):(lang==="zh"?"临时处理（未配置书库）":"Temporary processing (no library)"));
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
function payload(){const data=new FormData();if(!selectedBook())data.append("pdf",$("pdf").files[0]);data.append("notes",$("notes").value);return data;}
async function request(endpoint){
 const res=await fetch(selectedBook()?"/books/"+encodeURIComponent(selectedBook())+endpoint:endpoint,{method:"POST",headers:{"X-Library-Request":"1"},body:payload()});
 if(!res.ok){let message="HTTP "+res.status;try{const data=await res.json();message=data.detail||message;}catch{}throw new Error(message);}
 return res;
}
function validate(){const file=$("pdf").files[0];if((!file&&!selectedBook())||!$("notes").value.trim()){status(t("missing"),true);return false;}if(!selectedBook()&&file&&file.size>maxBookBytes){status(t("tooLarge"),true);return false;}return true;}
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
  const blob=lastBlob;clearPDF();lastBlob=blob;objectUrl=URL.createObjectURL(blob);
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

function selectedBook(){return $("books").value;}
async function checked(url, options={}) {
 const res=await fetch(url,{...options,headers:{"X-Library-Request":"1"}});
 if(!res.ok){let message="HTTP "+res.status;try{message=(await res.json()).detail||message;}catch{}throw new Error(message);}
 return res;
}
async function refreshBooks(){
 const previous=selectedBook();const data=await (await checked("/books")).json();
 $("books").replaceChildren(new Option("本次上传 / New upload",""));
 data.books.forEach(book=>$("books").add(new Option(book.name+" · "+book.extension+" · "+book.state,book.id)));
 if([...$("books").options].some(o=>o.value===previous))$("books").value=previous;
 $("quota").textContent=(data.used_bytes/1024/1024).toFixed(1)+" / "+(data.quota_bytes/1024/1024)+" MB · "+data.books.length+" / "+data.book_limit+" 本";
}
$("books").addEventListener("change",()=>{reset();$("extracted").textContent="";});
$("pdf").addEventListener("change",()=>{$("books").value="";$("extracted").textContent="";});
$("refreshBooks").addEventListener("click",()=>refreshBooks().catch(e=>status(e.message,true)));
$("saveBook").addEventListener("click",async()=>{
 const file=$("pdf").files[0];if(!file){status("请选择文件 / Choose a file",true);return;}
 if(file.size>maxBookBytes){status(t("tooLarge"),true);return;}
 $("saveBook").disabled=true;status(t("working"));
 try{const form=new FormData();form.append("file",file);const book=await(await checked("/books",{method:"POST",body:form})).json();await refreshBooks();$("books").value=book.id;reset();status("已保存，可以重复选择 / Saved for reuse");}
 catch(e){status(e.message,true);try{await refreshBooks();}catch{}}
 finally{$("saveBook").disabled=false;}
});
$("deleteBook").addEventListener("click",async()=>{
 if(!selectedBook())return;
 try{await checked("/books/"+encodeURIComponent(selectedBook()),{method:"DELETE"});await refreshBooks();reset();$("extracted").textContent="";status("已删除 / Deleted");}
 catch(e){status(e.message,true);}
});
$("extractText").addEventListener("click",async()=>{
 $("extractText").disabled=true;status(t("working"));
 try{let response;if(selectedBook()){response=await checked("/books/"+encodeURIComponent(selectedBook())+"/text");}
 else{const file=$("pdf").files[0];if(!file)throw new Error("请选择文件 / Choose a file");if(file.size>maxBookBytes)throw new Error(t("tooLarge"));const form=new FormData();form.append("file",file);response=await checked("/extract",{method:"POST",body:form});}
 const data=await response.json();$("extracted").textContent=data.sections.map(s=>"["+s.page+"]\n"+s.text).join("\n\n");status("文字提取完成 / Text extracted");}
 catch(e){status(e.message,true);}finally{$("extractText").disabled=false;}
});
(async()=>{try{const settings=await(await checked("/config")).json();libraryEnabled=settings.library_enabled;maxBookBytes=settings.max_book_bytes;translate();$("libraryPanel").hidden=!settings.library_enabled;if(settings.library_enabled)await refreshBooks();}catch(e){status(e.message,true);}})();
