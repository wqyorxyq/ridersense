// SPDX-License-Identifier: AGPL-3.0-only
let currentMode="live";
const $=id=>document.getElementById(id);
let token=sessionStorage.getItem('riderToken')||'', streaming=false, stream=null, seq=0, source='camera', seen=-1, lastGeneration=-1, uploadBusy=false;
let videoURL=null, lastVideoTime=null, replayResetBusy=false;
let modelsReady=false;
let settingsHydrated=false;
function englishMessage(text){
 let value=String(text??'');

 if(/\p{Script=Han}/u.test(value)){console.error(text);return 'An operation failed. See the browser console for technical details.'}
 return value;
}
function message(text){$('message').textContent=englishMessage(text)}
async function api(path,body,method='POST'){
 const headers={'x-rider-token':token};if(body!==undefined)headers['Content-Type']='application/json';
 const r=await fetch(path,{method,headers,body:body===undefined?undefined:JSON.stringify(body)});
 const data=await r.json();if(!r.ok)throw Error(data.detail||r.statusText);return data;
}
function action(id,fn){$(id).onclick=async()=>{try{await fn()}catch(e){message(e.message)}}}
action('load',async()=>{await api('/api/models/load',{mode:'da3'});message('Loading detection and DA3 models…')});
action('detect',async()=>{await api('/api/models/load',{mode:'detect'});message('Loading vehicle detection…')});
async function stopCapture(){streaming=false;if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}$('video').pause();$('video').srcObject=null;await api('/api/stop');}
async function resetSource(){await api('/api/source/reset');currentMode='live';lastVideoTime=null;$('calibrated').checked=false;$('focal').value='';seen=-1;}
action('stop',async()=>{await stopCapture();message('Capture and all automatic feedback stopped.')});
action('camera',async()=>{
 await stopCapture();await resetSource();
 if(!navigator.mediaDevices?.getUserMedia)throw Error('Camera access requires localhost or trusted HTTPS. Open the trusted HTTPS address on your phone.');
 stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:960},height:{ideal:540}},audio:false});
 stream.getTracks().forEach(t=>t.onended=()=>stopCapture().catch(e=>message(e.message)));$('video').srcObject=stream;await $('video').play();source='camera';streaming=true;message('Live camera started. Revalidate calibration after switching inputs.');
});
action('native-camera',async()=>{await stopCapture();await api('/api/camera/start');$('calibrated').checked=false;$('focal').value='';seen=-1;source='computer-camera';message('Starting the laptop camera. Analysis updates when models are ready.')});
async function playSelectedVideo(){
 if(!videoURL)throw Error('Choose a test video first.');
 await stopCapture();await resetSource();source='video-replay';
 const v=$('video');v.src=videoURL;v.currentTime=0;v.loop=$('video-loop').checked;
 await v.play();streaming=true;
 message('Video playing: wait for detections, then click Enable auto vibration. Selecting a video exits simulation and clears previous alerts.');
}
$('file').onclick=()=>{$('file').value=''};
$('file').onchange=async()=>{try{const file=$('file').files[0];if(!file)return;await stopCapture();if(videoURL)URL.revokeObjectURL(videoURL);videoURL=URL.createObjectURL(file);await playSelectedVideo()}catch(e){message(e.message)}};
action('replay',playSelectedVideo);
$('video-loop').onchange=()=>{$('video').loop=$('video-loop').checked};
$('video').onplay=()=>{if(source==='video-replay'&&currentMode==='live'&&!document.hidden)streaming=true};
$('video').onpause=()=>{if(streaming&&$('video').paused){streaming=false;api('/api/stop').catch(e=>message(e.message));message('Video paused; auto vibration disabled. Resume playback, then enable auto vibration again.')}};
$('video').onended=()=>{if($('video').ended){streaming=false;api('/api/stop').catch(e=>message(e.message));message('Video ended. Click Replay selected video or enable looping.')}};
$('video').onerror=()=>message('The browser cannot play this video. Try an H.264-encoded MP4 file.');
action('scan',async()=>{const s=await api('/api/haptics/scan');message(s.devices.length?`Detected ${s.devices.length} dots`:'No dots found. Check power, the data cable and the CP210x driver.')});
action('disarm',async()=>{await api('/api/haptics/disarm');message('Auto vibration disabled; camera analysis continues.')});
action('arm',async()=>{await api('/api/haptics/arm');message('Auto vibration enabled.')});
action('settings',async()=>{await api('/api/settings',{focal_ratio:$('focal').value?+$('focal').value:null,calibrated:$('calibrated').checked,include_people:$('people').checked,image_area_demo:$('area-demo').checked,input_mirrored:$('input-mirror').checked,intrinsics_fx:$('intrinsics-fx').value?+$('intrinsics-fx').value:null,intrinsics_cx:+$('intrinsics-cx').value,intrinsics_verified:$('intrinsics-verified').checked});message('Settings applied; auto vibration disabled.')});
action('calibrate',async()=>{if(!$('calibration-target').value)throw Error('Wait for DA3 to detect an object first.');const r=await api('/api/calibrate',{track_id:Number($('calibration-target').value),distance_m:Number($('known-distance').value)});$('focal').value=r.focal_ratio.toFixed(6);$('calibrated').checked=true;message('Single-point scale fit complete. Verify at another distance, then enable auto vibration.')});
action('pair',async()=>{token=$('token').value.trim();await api('/api/status',undefined,'GET');sessionStorage.setItem('riderToken',token);message('Paired successfully.')});
action('copy',async()=>{await navigator.clipboard.writeText(token);message('Pairing token copied. Share only with devices used for this demo.')});
async function capture(){
 if(currentMode==='live'&&streaming&&modelsReady&&!uploadBusy&&!replayResetBusy&&!$('video').paused&&$('video').readyState>=2){
  uploadBusy=true;
  try{const v=$('video');if(source==='video-replay'&&lastVideoTime!==null&&v.currentTime<lastVideoTime-.1){replayResetBusy=true;try{await api('/api/replay/reset')}finally{replayResetBusy=false}}lastVideoTime=v.currentTime;const c=$('capture'), scale=Math.min(1,960/v.videoWidth);c.width=Math.round(v.videoWidth*scale);c.height=Math.round(v.videoHeight*scale);c.getContext('2d').drawImage(v,0,0,c.width,c.height);
   const blob=await new Promise(resolve=>c.toBlob(resolve,'image/jpeg',.78));const form=new FormData();form.append('file',blob,'frame.jpg');
   const r=await fetch(`/api/frame?seq=${++seq}&source=${source}`,{method:'POST',headers:{'x-rider-token':token},body:form});if(!r.ok){const e=await r.json();message(e.detail)}
  }catch(e){message(e.message)}finally{uploadBusy=false}
 }
 setTimeout(capture,180);
}
const labels={car:'Car',motorcycle:'Motorcycle',bicycle:'Bicycle',bus:'Bus',truck:'Truck',person:'Person'};
const directions={left:'Left (edge)',rear_left:'Rear-left',rear:'Rear',rear_right:'Rear-right',right:'Right (edge)'};
for(const name of ['thermal-strength','light-brightness'])$(name).oninput=()=>$(name+'-value').textContent=$(name).value+'%';
async function thermalCommand(sign){await api('/api/haptics/thermal/'+$('manual-dot').value,{intensity:sign*Number($('thermal-strength').value)/100,seconds:Number($('thermal-seconds').value)});message(sign===0?'Thermal output stopped':`Dot ${$('manual-dot').value} ${sign>0?'Heating':'Cooling'} started; ${$('thermal-seconds').value} seconds until automatic stop.`)}
action('heat',()=>thermalCommand(1));action('cool',()=>thermalCommand(-1));action('thermal-off',()=>thermalCommand(0));
action('temperature',async()=>{const t=await api('/api/haptics/temperature/'+$('manual-dot').value,undefined,'GET');$('temperature-readout').textContent=`Contact ${t.skin} °C · Heatsink ${t.sink} °C`});
async function lightCommand(off){const c=$('light-color').value;await api('/api/haptics/light/'+$('manual-dot').value,{red:parseInt(c.slice(1,3),16),green:parseInt(c.slice(3,5),16),blue:parseInt(c.slice(5,7),16),brightness:off?0:Number($('light-brightness').value)/100});message(off?'LEDs off':'LED color applied')}
action('light-apply',()=>lightCommand(false));action('light-off',()=>lightCommand(true));
async function poll(){
 try{if(token){const s=await api('/api/status',undefined,'GET');modelsReady=s.model_status.startsWith('ready:');$('model').textContent=s.model_status;$('hardware').textContent=s.haptics.devices.length?`${s.haptics.devices.length} dots · ${s.haptics.armed?'Auto feedback on':'Auto feedback off'}`:'No USB dots detected';
   if(s.depth_download){$('download-status').textContent=s.depth_download.ready?'DA3 weights present. Use the download command to verify integrity.':`Optional DA3 weights: ${s.depth_download.downloaded_mb} / ${s.depth_download.total_mb} MB`;$('load').disabled=!s.depth_download.ready||s.model_status==='loading'}
   $('detect').disabled=s.model_status==='loading';
   if(!settingsHydrated){$('focal').value=s.settings.focal_ratio??'';$('calibrated').checked=s.settings.calibrated;$('people').checked=s.settings.include_people;$('area-demo').checked=!!s.settings.image_area_demo;$('input-mirror').checked=!!s.settings.input_mirrored;$('intrinsics-fx').value=s.settings.intrinsics_fx??'';$('intrinsics-cx').value=s.settings.intrinsics_cx??.5;$('intrinsics-verified').checked=!!s.settings.intrinsics_verified;settingsHydrated=true}
   $('dots').replaceChildren(...s.haptics.devices.map(d=>{const b=document.createElement('button');b.textContent=`Dot ${d.id}`;if(s.haptics.armed&&s.haptics.target&&s.haptics.outputs?.[d.id]>0)b.className='active';b.onclick=()=>api(`/api/haptics/test/${d.id}`).then(()=>message(`Dot ${d.id} Short pulse sent`)).catch(e=>message(e.message));return b}));
   const manualId=$('manual-dot').value, thermal=s.haptics.thermal?.[manualId], temperature=s.haptics.temperatures?.[manualId];
   $('thermal-status').textContent=thermal?`Dot ${manualId} ${thermal.intensity>0?'Heating':'Cooling'} · Timed output`:`Dot ${manualId} Thermal output off`;
   if(temperature)$('temperature-readout').textContent=`Contact ${temperature.skin} °C · Heatsink ${temperature.sink} °C (last reading)`;else $('temperature-readout').textContent='Temperature not read';
   if(s.error)message(s.error);else if(s.haptics.error)message(s.haptics.error);
   renderAlert(s);renderAlertReason(s);const r=s.result;$('mode').textContent=s.mode==='simulation'?'Simulation · Not live':!r?'Waiting for frames':r.stale?'Frame expired':r.metric&&!r.image_area_demo?'Distance + image-area risk score':'Area + growth score · Not ranging';
   if(r){$('latency').textContent=`Analysis ${r.inference_ms} ms · Pipeline ${r.pipeline_ms??"—"} ms · Frame age ${r.age_ms} ms`;$('source').textContent=r.source==='video-replay'?'Recorded video replay':r.source==='computer-camera'?'Live laptop camera':r.source==='integration-test'?'Test image (not live)':'Live camera';$('scale').textContent=r.image_area_demo?'Area + growth · Not distance':r.metric?'Estimated distance (m)':'Area + growth · Distance uncalibrated';
    const target=$('calibration-target'),selected=target.value,targets=r.objects.filter(o=>o.track_id!==null&&o.depth_value!==null);target.replaceChildren(new Option(targets.length?'Choose a calibration target':'Waiting for an object with depth',''),...targets.map(o=>new Option(`${directions[o.direction]} · ${labels[o.label]||o.label} #${o.track_id}`,o.track_id)));if(targets.some(o=>String(o.track_id)===selected))target.value=selected;else if(targets.length===1)target.value=String(targets[0].track_id);
    if(r.seq!==seen||s.generation!==lastGeneration){seen=r.seq;lastGeneration=s.generation;const image=new Image();image.onload=()=>{const c=$('output');c.width=r.width;c.height=r.height;const ctx=c.getContext('2d');ctx.save();if($('preview-mirror').checked){ctx.translate(c.width,0);ctx.scale(-1,1)}ctx.drawImage(image,0,0);ctx.restore();ctx.lineWidth=3;ctx.font='16px system-ui';for(const o of r.objects){ctx.strokeStyle=o.level===2?'#ff8294':o.level===1?'#ffd078':'#8df2c8';let [x,y,x2,y2]=o.box;if($('preview-mirror').checked){[x,x2]=[r.width-x2,r.width-x]}ctx.strokeRect(x,y,x2-x,y2-y);ctx.fillStyle=ctx.strokeStyle;ctx.fillText(`#${o.track_id??'—'} ${directions[o.direction]} Risk ${o.risk_score??0} ${labels[o.label]||o.label} ${r.image_area_demo?'Image area '+Math.round(o.image_fraction*100)+'%':o.distance_m===null?'Depth uncalibrated':o.distance_m+' m'}`,x,Math.max(y-8,20))}};image.src='data:image/jpeg;base64,'+r.image;$('placeholder').hidden=true;
      $('objects').replaceChildren(...r.objects.map(o=>{const row=document.createElement('div');row.className='object '+(o.level===2?'critical':o.level===1?'warn':'');row.textContent=`${directions[o.direction]} · ${labels[o.label]||o.label} #${o.track_id??'—'} ｜ ${r.image_area_demo?'Image area '+Math.round(o.image_fraction*100)+'%':o.distance_m===null?'Distance uncalibrated':o.distance_m+' m'} ｜ Risk ${o.risk_score??0}/100 · ${['Low','Medium','High'][o.level]} ｜ Closing ${o.closing_mps===null?'Unavailable':o.closing_mps+' m/s'} ｜ ${o.direction_method==='intrinsics-angle'?'Calibrated angle':'Approximate image zone'}`;return row}));if(!r.objects.length)$('objects').textContent='No objects detected in this frame';
      if(r.depth_image){$('depth').src='data:image/jpeg;base64,'+r.depth_image}else $('depth').removeAttribute('src');
    }
   }
 }}catch(e){message('Connection: '+e.message)}setTimeout(poll,500);
}
document.addEventListener('visibilitychange',()=>{if(document.hidden&&streaming){streaming=false;api('/api/stop').catch(()=>{})}});
(async()=>{try{const r=await fetch('/api/session');if(r.ok){token=(await r.json()).token;sessionStorage.setItem('riderToken',token)}}catch(e){message(e.message)}poll();capture()})();


$('preview-mirror').onchange=()=>{$('video').style.transform=$('preview-mirror').checked?'scaleX(-1)':'';seen=-1};
$('sim-score').oninput=()=>$('sim-score-value').textContent=$('sim-score').value;
action('simulate',async()=>{await stopCapture();await api('/api/simulation',{direction:$('sim-direction').value,score:+$('sim-score').value,hardware:$('sim-hardware').checked});message('Simulation mode: live input is stopped.')});
action('live-mode',async()=>{await stopCapture();await api('/api/live');currentMode='live';seen=-1;message('Back in live mode. Restart the camera.')});
function renderAlert(s){
 currentMode=s.mode;
 const sim=s.mode==='simulation',visible=s.result&&!s.result.stale?[...s.result.objects].sort((a,b)=>b.risk_score-a.risk_score)[0]:null,target=sim?s.simulation:(s.haptics.target||visible);
 const out=sim?s.simulation?.outputs:s.haptics.outputs;
 $('alert-mode').textContent=sim?'Simulation preview · Not live':s.haptics.armed?'Auto alerts on':'Auto alerts off';
 const c=$('topview'),ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);ctx.font='16px system-ui';ctx.textAlign='center';
 ctx.strokeStyle='#8df2c8';ctx.fillStyle='#8df2c8';ctx.beginPath();ctx.arc(320,100,30,0,Math.PI*2);ctx.stroke();ctx.fillText('Rider',320,105);ctx.fillText('↑ Forward',320,35);ctx.fillText('Camera ↓ Rear-facing',320,158);
 const positions={left:[90,100],rear_left:[170,235],rear:[320,290],rear_right:[470,235],right:[550,100]};
 for(const [name,[x,y]] of Object.entries(positions)){ctx.fillStyle=target?.direction===name?'#ff8294':'#8c9da8';ctx.fillText(directions[name],x,y);if(target?.direction===name)ctx.fillText(`Risk ${target.risk_score??0} · #${target.track_id??'Simulated'}`,x,y+24)}
 for(const [i,x,y] of [[1,240,88],[2,268,187],[3,372,187],[4,400,88]]){const v=out?.[i]||0;ctx.fillStyle=v?'#ffd078':'#52616b';ctx.fillText(`Dot ${i}: ${Math.round(v*100)}%`,x,y)}
 $('channel-state').textContent=(sim?'Simulation plan (not current output): ':'Current requested intensity: ')+[1,2,3,4].map(i=>`Dot ${i} ${Math.round((out?.[i]||0)*100)}%`).join(' · ')+(sim?'; Current hardware request: '+[1,2,3,4].map(i=>`Dot ${i} ${Math.round((s.haptics.outputs?.[i]||0)*100)}%`).join(' / '):'');
 const cmd=s.haptics.last_command;
 $('command-state').textContent=cmd?`Last serial writes returned · Prepare + send ${cmd.write_span_ms} ms · Start command gap ${cmd.start_span_ms??"—"} ms; SDK nominal levels: ${Object.entries(cmd.channels).map(([i,v])=>`Dot ${i} ${Math.round(v.nominal*100)}%`).join(' / ')}. No physical execution feedback.`:'No serial writes recorded. Simulation graphics do not confirm physical output.';
 if(!s.result){$('objects').textContent=sim?'Simulation mode; no live detections':'Waiting for a fresh frame';$('placeholder').hidden=false;}
}

function renderAlertReason(s){
 const h=s.haptics,r=s.result;
 let reason;
 if(h.error)reason='Device error: '+englishMessage(h.error);
 else if(s.mode==='simulation')reason='Simulation mode: video is not being analyzed. Choose or replay a video to switch. Physical simulation pulses last up to 1.5 seconds.';
 else if(h.devices.length<4)reason=`Connected ${h.devices.length}/4 dots; scan the controller.`;
 else if(!r)reason='No analyzed frames yet. Load models and keep the video playing.';
 else if(r.stale)reason='Frame expired; alerts stopped. Keep this page in the foreground and resume playback.';
 else if(!h.armed)reason='Auto vibration is off. Click Enable auto vibration. Selecting a video, scanning, pausing or applying settings disables it.';
 else if(!r.objects.length)reason='No objects detected. For a video of people, enable person detection, apply settings, then enable auto vibration again.';
 else if(r.objects.every(o=>o.level===0))reason=`Below alert threshold. Highest score: ${Math.max(...r.objects.map(o=>o.risk_score||0)).toFixed(1)}; must exceed 40.`;
 else if(h.target&& !Object.values(h.outputs||{}).some(v=>v>0))reason='The target is at the left or right edge with medium risk. This combination has no vibration assigned.';
 else if(Object.values(h.outputs||{}).some(v=>v>0))reason='Vibration requested: '+Object.entries(h.outputs).filter(([k,v])=>v>0).map(([k,v])=>`Dot ${k} ${Math.round(v*100)}%`).join(' / ');
 else reason='Waiting for the next alert decision.';
 $('alert-reason').textContent=reason;
 if(source==='video-replay')$('video-status').textContent=`Video ${$('video').paused?'Paused':'Playing'} · ${streaming?'Sampling':'Sampling stopped'} · ${modelsReady?'Models ready':'Load models first'}. Keep this page in the foreground.`;
}
