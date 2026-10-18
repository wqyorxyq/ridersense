// UI logic test with a strict DOM stub; does not claim visual browser coverage.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('static/index.html','utf8');
function element(){return {value:'',checked:false,style:{},children:[],textContent:'',
 replaceChildren(...v){this.children=v},add(){},pause(){},removeAttribute(){},
 getContext(){return new Proxy({},{get:()=>()=>{}})}}}
const nodes=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],element()]));
let status={model_status:'ready:da3:cuda:0',mode:'live',generation:1,settings:{},
 depth_download:{ready:true},haptics:{devices:[],outputs:{},thermal:{},temperatures:{}},
 result:{seq:1,width:640,height:480,age_ms:50,inference_ms:80,pipeline_ms:100,metric:false,image:'',
 objects:[{box:[10,10,80,80],track_id:1,label:'car',direction:'rear_left',risk_score:80,level:2,
 depth_value:null,distance_m:null,closing_mps:null,image_fraction:.1,direction_method:'image-bands'}]}};
const context={document:{getElementById(id){assert.ok(nodes[id],`Missing DOM id ${id}`);return nodes[id]},
 createElement:element,addEventListener(){}},sessionStorage:{getItem(){return ''},setItem(){}},
 Option:class {constructor(text,value){this.text=text;this.value=value}},
 Image:class {set src(v){this.onload()}},setTimeout(){},console,
 fetch:async path=>({ok:true,json:async()=>path==='/api/session'?{token:'test'}:status})};
vm.createContext(context);vm.runInContext(fs.readFileSync('static/app.js','utf8'),context);
(async()=>{await new Promise(setImmediate);await vm.runInContext('poll()',context);
 assert.match(nodes.objects.children[0].textContent,/80\/100/);
 assert.match(nodes['alert-reason'].textContent,/0\/4/);
 assert.match(nodes.mode.textContent,/Not ranging/);
 status={...status,mode:'simulation',result:null,simulation:{direction:'rear',risk_score:60,outputs:{2:.4,3:.4}}};
 await vm.runInContext('poll()',context);
 assert.match(nodes.mode.textContent,/Simulation/);assert.match(nodes['channel-state'].textContent,/Dot 2 40%/);
 status={...status,simulation:null};await vm.runInContext('poll()',context);
 assert.match(nodes['channel-state'].textContent,/Dot 2 0%/);
 assert.doesNotMatch(nodes.message.textContent,/Connection:/);
 status={...status,mode:'live',haptics:{...status.haptics,devices:[1,2,3,4],armed:false},result:{source:'video-replay',objects:[],seq:2,width:640,height:480}};
 await vm.runInContext('poll()',context);assert.match(nodes['alert-reason'].textContent,/Auto vibration is off/);
 vm.runInContext("source='video-replay';currentMode='live';streaming=false",context);nodes.video.onplay();assert.equal(vm.runInContext('streaming',context),true);
 nodes.video.paused=true;nodes.video.onpause();assert.equal(vm.runInContext('streaming',context),false);
 nodes.video.paused=false;nodes.video.onplay();assert.equal(vm.runInContext('streaming',context),true);
 console.log('UI smoke passed: live result, simulation, stopped channels and required DOM nodes.');
})().catch(e=>{console.error(e);process.exitCode=1});
