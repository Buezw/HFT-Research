// Global namespace and common utils
window.HFT = {
  selectedFactor: null,
  lastArtifactsDir: null,
  darkLayout: { paper_bgcolor:'#1c1c1c', plot_bgcolor:'#1c1c1c', font:{color:'#fff'}, margin:{t:40,r:10,b:40,l:50} },
  fmt: (x,d=4)=>{ if(x==null||x===undefined) return "-"; if(typeof x!=='number') return x; if(!isFinite(x)) return String(x); return x.toFixed(d); },
  setStatus: (id,msg,kind='ok')=>{ const el=document.getElementById(id); el.textContent=msg; el.style.color=(kind==='loading')?'#ffd166':(kind==='err'?'#ff6b6b':'#9be564'); }
};

window.addEventListener('DOMContentLoaded', ()=>{
  HFT.loadFactors();
  HFT.loadModels();
});
