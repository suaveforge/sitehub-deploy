(()=>{
  'use strict';
  if(window.SITEHUB_ANALYTICS?.active)return;

  const script=document.currentScript;
  const projectId=(script?.dataset?.sitehubProject||window.SITEHUB_PROJECT_ID||'').trim();
  if(!/^p\d{2,}$/.test(projectId)){
    window.SITEHUB_ANALYTICS={active:false,error:'missing-project-id'};
    return;
  }

  const API=(script?.dataset?.sitehubApi||'https://api-sitehub.suaveforge.com:18464').replace(/\/$/,'')+'/api/v1/analytics/events';
  const prefix=`sitehub:${projectId}:`;
  const QUEUE_KEY=prefix+'pending_pageviews_v1';
  const ACK_KEY=prefix+'pageview_acks_v1';
  const MAX_QUEUE=60,MAX_ACKS=120;
  let flushing=false,memoryQueue=[],memoryAcks=[],lastLocation='';

  const uuid=()=>globalThis.crypto?.randomUUID?crypto.randomUUID():'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.random()*16|0,v=c==='x'?r:(r&3|8);return v.toString(16)});
  const get=(store,key)=>{try{let v=store.getItem(key);if(!v){v=uuid();store.setItem(key,v)}return v}catch{return uuid()}};
  const readJson=(key,fallback)=>{try{const raw=localStorage.getItem(key);if(!raw)return fallback;return JSON.parse(raw)??fallback}catch{return fallback}};
  const writeJson=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value));return true}catch{return false}};
  const ackedIds=()=>{const saved=readJson(ACK_KEY,memoryAcks);const ids=Array.isArray(saved)?saved:memoryAcks;memoryAcks=ids.filter(x=>typeof x==='string').slice(0,MAX_ACKS);return new Set(memoryAcks)};
  const rememberAck=id=>{memoryAcks=[id,...ackedIds()].slice(0,MAX_ACKS);writeJson(ACK_KEY,memoryAcks)};
  const readQueue=()=>{const saved=readJson(QUEUE_KEY,memoryQueue);const rows=Array.isArray(saved)?saved:memoryQueue;memoryQueue=rows.filter(x=>x&&x.id&&x.body).slice(-MAX_QUEUE);return [...memoryQueue]};
  const writeQueue=rows=>{memoryQueue=(rows||[]).slice(-MAX_QUEUE);writeJson(QUEUE_KEY,memoryQueue)};

  const visitorId=get(localStorage,prefix+'vid');
  const sessionId=get(sessionStorage,prefix+'sid');
  const params=new URLSearchParams(location.search);
  let first={};
  try{first=JSON.parse(sessionStorage.getItem(prefix+'touch')||'{}')}catch{}
  if(!first?.landingPage){
    first={
      landingPage:location.pathname+location.search,
      referrer:document.referrer||'',
      utmSource:params.get('utm_source')||'',
      utmMedium:params.get('utm_medium')||'',
      utmCampaign:params.get('utm_campaign')||''
    };
    try{sessionStorage.setItem(prefix+'touch',JSON.stringify(first))}catch{}
  }

  const browser=()=>{
    const ua=navigator.userAgent||'';
    if(/Edg\//.test(ua))return 'Edge';
    if(/OPR\//.test(ua))return 'Opera';
    if(/Chrome\//.test(ua))return 'Chrome';
    if(/Firefox\//.test(ua))return 'Firefox';
    if(/Safari\//.test(ua)&&!/Chrome\//.test(ua))return 'Safari';
    return 'Other';
  };
  const deviceType=()=>innerWidth<768?'mobile':innerWidth<1100?'tablet':'desktop';
  const base=()=>({
    projectId,visitorId,sessionId,...first,
    deviceType:deviceType(),browser:browser(),
    language:(navigator.language||'').slice(0,80),
    timezone:(Intl.DateTimeFormat().resolvedOptions().timeZone||'').slice(0,120),
    screenWidth:screen?.width||0,screenHeight:screen?.height||0
  });

  const removeFromQueue=id=>writeQueue(readQueue().filter(x=>x.id!==id));
  const markAck=id=>{rememberAck(id);removeFromQueue(id)};
  const post=async item=>{
    try{
      const r=await fetch(API,{method:'POST',headers:{'Content-Type':'text/plain;charset=UTF-8'},credentials:'omit',keepalive:true,cache:'no-store',body:item.body});
      if(r.ok){markAck(item.id);return true}
    }catch{}
    return false;
  };
  const flush=async()=>{
    if(flushing)return;
    flushing=true;
    try{
      const acks=ackedIds();
      const queue=readQueue().filter(x=>!acks.has(x.id));
      for(const item of queue){
        item.attempts=Number(item.attempts||0)+1;
        writeQueue(queue);
        if(!await post(item))break;
      }
    }finally{flushing=false}
  };
  const beaconPending=()=>{
    if(!navigator.sendBeacon)return;
    const acks=ackedIds();
    for(const item of readQueue()){
      if(acks.has(item.id))continue;
      try{navigator.sendBeacon(API,new Blob([item.body],{type:'text/plain;charset=UTF-8'}))}catch{}
    }
  };

  const capture=()=>{
    const locationKey=location.pathname+location.search+location.hash;
    if(locationKey===lastLocation)return;
    lastLocation=locationKey;
    const pageViewId=uuid();
    const payload={
      ...base(),eventType:'page_view',hostname:location.hostname,pathname:location.pathname,
      pageTitle:document.title||'',referrer:first.referrer||'',
      metadata:{pageViewId,url:location.pathname+location.search,captureVersion:'20260909-sitehub-01',capturedAt:new Date().toISOString()}
    };
    const item={id:pageViewId,body:JSON.stringify(payload),createdAt:Date.now(),attempts:0};
    const queue=readQueue().filter(x=>!ackedIds().has(x.id));
    if(!queue.some(x=>x.id===item.id)){queue.push(item);writeQueue(queue)}
    void flush();
  };

  const routeCapture=()=>setTimeout(capture,0);
  const wrapHistory=name=>{
    const original=history[name];
    if(typeof original!=='function')return;
    history[name]=function(...args){const out=original.apply(this,args);routeCapture();return out};
  };
  wrapHistory('pushState');
  wrapHistory('replaceState');
  addEventListener('popstate',routeCapture,{passive:true});
  addEventListener('hashchange',routeCapture,{passive:true});
  addEventListener('online',()=>void flush(),{passive:true});
  addEventListener('pagehide',beaconPending,{capture:true});
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')beaconPending();else void flush()},{capture:true});

  capture();
  setTimeout(()=>void flush(),1200);
  setTimeout(()=>void flush(),4500);
  window.SITEHUB_ANALYTICS={active:true,projectId,flush,capture};
})();
