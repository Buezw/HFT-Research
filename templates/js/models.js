// Models: list & train
(function(H){
  H.loadModels = async function(){
    const res = await fetch('/api/models'); const data = await res.json();
    const sel = document.getElementById('model-select'); sel.innerHTML = '';
    for (const [name, meta] of Object.entries(data)){
      const opt = document.createElement('option'); opt.value = name; opt.textContent = `${name} - ${meta.desc}`; sel.appendChild(opt);
    }
  };

  H.clearTrain = function(){
    ['model-name','model-task','model-acc','model-auc','deg-note'].forEach(id => document.getElementById(id).textContent='-');
    Plotly.purge('roc-plot');
  };

  H.clearBacktest = function(){
    ['pnl-plot','dd-plot','pred-plot','pr-plot','calib-plot','cm-plot','hist-plot'].forEach(id => Plotly.purge(id));
    document.getElementById('kpi').innerHTML = '';
    H.setStatus('backtest-status','', 'ok');
  };

  H.trainModel = async function(){
    const model = document.getElementById('model-select').value;
    if (!H.selectedFactor){ alert('先选择一个因子'); return; }
    const horizon = +document.getElementById('inp-horizon').value;
    const eps = parseFloat(document.getElementById('inp-eps').value);
    const drop_equal = document.getElementById('inp-drop-equal').checked;
    const scale = document.getElementById('inp-scale').checked;

    const q = new URLSearchParams({factor:H.selectedFactor, model, horizon, eps, scale: scale?'true':'false'});
    if (drop_equal) q.set('drop_equal','true');

    H.setStatus('train-status','Training…','loading');
    H.clearTrain(); H.clearBacktest(); H.lastArtifactsDir = null;

    try{
      const res = await fetch(`/api/train?${q.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const task = data.task || 'classification';
      const m = data.metrics || {};
      document.getElementById('model-name').textContent = data.model || model;
      document.getElementById('model-task').textContent = task;
      document.getElementById('model-acc').textContent = H.fmt(m.accuracy ?? m.Accuracy ?? NaN, 4);
      document.getElementById('model-auc').textContent = H.fmt(m.auc ?? m.AUC ?? NaN, 4);

      if (data.roc && Array.isArray(data.roc.fpr)){
        const trace={x:data.roc.fpr,y:data.roc.tpr,mode:'lines',type:'scatter',name:'ROC'};
        const diag ={x:[0,1],y:[0,1],mode:'lines',type:'scatter',name:'Chance',line:{dash:'dot'}};
        Plotly.newPlot('roc-plot',[trace,diag],
          Object.assign({}, H.darkLayout, {title:'ROC Curve', xaxis:{title:'FPR',range:[0,1]}, yaxis:{title:'TPR',range:[0,1]}}),
          {responsive:true});
      }

      H.lastArtifactsDir = data.artifacts_dir || null;
      H.setStatus('train-status','Done.','ok');
    }catch(err){
      H.setStatus('train-status',`Error: ${err.message}`,'err');
      console.error(err);
    }
  };
})(window.HFT);
