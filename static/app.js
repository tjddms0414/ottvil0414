const $ = s => document.querySelector(s);
const canvas = $('#canvas'), ctx = canvas.getContext('2d');
let photo = null, upload = null, selection = null, strokes = [], mode = 'rect', drawing = false, start = null, current = null, resultURL = null, busy = false;
const status = message => { $('#status').textContent = message; };
function setTab(tab) {
  if (tab === 'result' && !resultURL) return;
  canvas.hidden = tab !== 'original'; $('#result').hidden = tab !== 'result';
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
}
function invalidate() {
  if (resultURL) URL.revokeObjectURL(resultURL);
  resultURL = null; $('#result').removeAttribute('src'); $('#download').disabled = true;
  $('[data-tab=result]').disabled = true; setTab('original');
  $('#step3').classList.remove('active');
}
function render() {
  if (!photo) return;
  ctx.clearRect(0,0,canvas.width,canvas.height); ctx.drawImage(photo,0,0,canvas.width,canvas.height);
  if(selection) {
    const {x,y,w,h} = selection;
    ctx.fillStyle='rgba(35,45,30,.23)'; ctx.beginPath(); ctx.rect(0,0,canvas.width,canvas.height); ctx.rect(x*canvas.width,y*canvas.height,w*canvas.width,h*canvas.height); ctx.fill('evenodd');
    ctx.strokeStyle='#ed724d'; ctx.lineWidth=2; ctx.setLineDash([7,5]); ctx.strokeRect(x*canvas.width,y*canvas.height,w*canvas.width,h*canvas.height); ctx.setLineDash([]);
  }
  for(const s of strokes) {
    ctx.strokeStyle=s.mode==='keep'?'rgba(75,170,100,.7)':'rgba(235,95,80,.7)'; ctx.fillStyle=ctx.strokeStyle; ctx.lineWidth=s.size*canvas.width; ctx.lineCap='round';ctx.lineJoin='round';
    ctx.beginPath(); s.points.forEach((p,i)=> i ? ctx.lineTo(p[0]*canvas.width,p[1]*canvas.height):ctx.moveTo(p[0]*canvas.width,p[1]*canvas.height));ctx.stroke();
    if(s.points.length===1){ctx.beginPath();ctx.arc(s.points[0][0]*canvas.width,s.points[0][1]*canvas.height,ctx.lineWidth/2,0,Math.PI*2);ctx.fill();}
  }
}
async function load(file) {
  if (busy || !file) return;
  if(!['image/jpeg','image/png','image/webp'].includes(file.type)){status('JPG, PNG, WEBP 사진을 선택해 주세요.');return;}
  if(file.size>20*1024*1024){status('20MB 이하의 사진을 선택해 주세요.');return;}
  const url=URL.createObjectURL(file), img=new Image();
  img.onload=()=>{
    URL.revokeObjectURL(url);
    if(img.naturalWidth*img.naturalHeight>40000000){status('4천만 화소 이하의 사진을 선택해 주세요.');return;}
    upload=file;photo=img;selection=null;strokes=[];invalidate();
    const scale=Math.min(1,1000/Math.max(img.naturalWidth,img.naturalHeight));
    canvas.width=Math.round(img.naturalWidth*scale);canvas.height=Math.round(img.naturalHeight*scale);
    $('#empty').hidden=true;$('#image-wrap').hidden=false;$('#filename').textContent=file.name;
    $('#dimensions').textContent=`${img.naturalWidth} × ${img.naturalHeight} PX`;
    $('#step2').classList.add('active');$('#process').disabled=true;render();status('제품 전체를 감싸도록 사진 위에서 드래그하세요.');
  };
  img.onerror=()=>{URL.revokeObjectURL(url);status('사진을 읽을 수 없습니다. 다른 파일을 선택해 주세요.');};img.src=url;
}
$('#upload').onclick=$('#choose').onclick=()=>{if(!busy)$('#file').click();};
$('#file').onchange=e=>{load(e.target.files[0]);e.target.value='';};
const drop=$('#dropzone');
['dragenter','dragover'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add('drag');}));
['dragleave','drop'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.remove('drag');if(t==='drop')load(e.dataTransfer.files[0]);}));
document.querySelectorAll('.tool').forEach(b=>b.onclick=()=>{if(busy)return;mode=b.dataset.mode;document.querySelectorAll('.tool').forEach(t=>t.classList.toggle('selected',t===b));setTab('original');});
function point(e){const r=canvas.getBoundingClientRect();return [Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))];}
canvas.onpointerdown=e=>{
 if(!photo||busy)return;
 if(mode!=='rect'&&!selection){status('먼저 영역 선택으로 제품을 감싸 주세요.');return;}
 invalidate();drawing=true;canvas.setPointerCapture(e.pointerId);start=point(e);
 if(mode==='rect'){selection={x:start[0],y:start[1],w:0,h:0};strokes=[];}
 else{current={mode,size:Number($('#brush').value)/canvas.getBoundingClientRect().width,points:[start]};strokes.push(current);}render();
};
canvas.onpointermove=e=>{if(!drawing)return;const p=point(e);if(mode==='rect')selection={x:Math.min(start[0],p[0]),y:Math.min(start[1],p[1]),w:Math.abs(p[0]-start[0]),h:Math.abs(p[1]-start[1])};else current.points.push(p);render();};
function finish(){if(!drawing)return;drawing=false;current=null;$('#process').disabled=!selection||selection.w<.01||selection.h<.01;status($('#process').disabled?'제품 영역을 조금 더 크게 선택해 주세요.':'제품이 선택됐어요. 브러시로 보정하거나 화이트 배경을 만들어 보세요.');}
canvas.onpointerup=finish;canvas.onpointercancel=finish;
$('#undo').onclick=()=>{if(busy)return;invalidate();if(strokes.length)strokes.pop();else selection=null;$('#process').disabled=!selection;render();status('마지막 지정을 취소했어요.');};
$('#shadow').oninput=e=>{$('#shadow-value').textContent=e.target.value+'%';if(resultURL){invalidate();status('그림자 설정이 바뀌었어요. 배경 만들기를 다시 눌러 주세요.');}};
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>setTab(b.dataset.tab));
$('#process').onclick=async()=>{
 if(!upload||!selection||busy)return;
 busy=true;$('#loading').hidden=false;$('#process').disabled=true;$('#shadow').disabled=true;$('#undo').disabled=true;
 status('배경을 분리하고 있어요. 잠시만 기다려 주세요.');
 const data=new FormData();data.append('file',upload);data.append('selection',JSON.stringify(selection));data.append('strokes',JSON.stringify(strokes));data.append('shadow',$('#shadow').value);
 try{
  const response=await fetch('/api/process',{method:'POST',body:data});
  if(!response.ok){let message='처리하지 못했습니다. 다시 시도해 주세요.';try{const err=await response.json();if(typeof err.detail==='string')message=err.detail;}catch{}throw new Error(message);}
  invalidate();resultURL=URL.createObjectURL(await response.blob());$('#result').src=resultURL;$('[data-tab=result]').disabled=false;$('#download').disabled=false;setTab('result');$('#step3').classList.add('active');status('완성됐어요. 가장자리를 확인하고 PNG로 저장하세요.');
 }catch(error){status(error.message||'서버 연결을 확인해 주세요.');}
 finally{busy=false;$('#loading').hidden=true;$('#process').disabled=false;$('#shadow').disabled=false;$('#undo').disabled=false;}
};
$('#download').onclick=()=>{if(!resultURL)return;const a=document.createElement('a');a.href=resultURL;a.download=(upload.name.replace(/\.[^.]+$/,'')||'product')+'-white-studio.png';a.click();};
$('#help').onclick=()=>$('#guide').showModal();$('#close-guide').onclick=()=>$('#guide').close();
