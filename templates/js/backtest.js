// Backtest & charts
(function(H){
  H.backtestModel = async function(){
    const model = document.getElementById('model-select').value;
    const horizon = +document.getElementById('inp-horizon').value;

    H.setStatus('backtest-status','Backtesting…','loading');
    H.clearBacktest();

    const q = new URLSearchParams({horizon});
    if (H.lastArtifactsDir) q.set('artifacts_dir', H.lastArtifactsDir);
    else {
      if (!H.selectedFactor){ alert('先选择一个因子'); return; }
      q.set('factor', H.selectedFactor);
      q.set('model', model);
    }

    try{
      const res = await fetch(`/api/backtest?${q.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // KPI badges
      const k = data.risk || {}; const c = data.classification || {};
      document.getElementById('kpi').innerHTML = [
        H.badge('Max Drawdown', k.max_drawdown),
        H.badge('Sharpe(step)', k.sharpe_step),
        H.badge('Exposure', k.exposure),
        H.badge('Turnover', k.turnover),
        H.badge('Precision@thr', c.precision_at_threshold),
        H.badge('Recall@thr', c.recall_at_threshold),
        H.badge('F1@thr', c.f1_at_threshold),
        H.badge('AP', c.average_precision),
        H.badge('Brier', c.brier),
        H.badge('Threshold', data.threshold)
      ].join('');

      // 1) cumulative PnL
      Plotly.newPlot('pnl-plot', [{x:data.series.ts, y:data.series.pnl, type:'scatter', mode:'lines', name:'PnL'}],
        Object.assign({}, H.darkLayout, {title:'Cumulative PnL (Test 1/6)', xaxis:{title:'Time'}, yaxis:{title:'PnL'}}), {responsive:true});

      // 2) drawdown
      Plotly.newPlot('dd-plot', [{x:data.series.ts, y:data.series.drawdown, type:'scatter', mode:'lines', name:'Drawdown'}],
        Object.assign({}, H.darkLayout, {title:'Drawdown (Test 1/6)', xaxis:{title:'Time'}, yaxis:{title:'Drawdown'}}), {responsive:true});

      // 3) prediction vs truth
      const predTraces = [];
      if (data.series.y_prob){
        predTraces.push({x:data.series.ts, y:data.series.y_prob, type:'scatter', mode:'lines', name:'Prob(1)'});
        predTraces.push({x:[data.series.ts[0], data.series.ts[data.series.ts.length-1]], y:[data.threshold, data.threshold],
                         type:'scatter', mode:'lines', name:`Threshold=${H.fmt(data.threshold,3)}`, line:{dash:'dot'}});
      } else {
        predTraces.push({x:data.series.ts, y:data.series.signals, type:'scatter', mode:'lines', name:'Signal (0/1)'});
      }
      predTraces.push({x:data.series.ts, y:data.series.y_test, type:'scatter', mode:'markers', name:'Truth (0/1)', marker:{size:5, opacity:0.7}});
      Plotly.newPlot('pred-plot', predTraces,
        Object.assign({}, H.darkLayout, {title:'Prediction vs Truth (Test 1/6)', xaxis:{title:'Time'}, yaxis:{title:'Prob / Class', range:[0,1]}}),
        {responsive:true});

      // 4) PR
      if (data.curves && data.curves.pr){
        Plotly.newPlot('pr-plot', [{x:data.curves.pr.recall, y:data.curves.pr.precision, type:'scatter', mode:'lines', name:'PR'}],
          Object.assign({}, H.darkLayout, {title:`Precision–Recall (AP=${H.fmt(c.average_precision,3)})`, xaxis:{title:'Recall', range:[0,1]}, yaxis:{title:'Precision', range:[0,1]}}),
          {responsive:true});
      } else {
        document.getElementById('pr-plot').innerHTML = '<div style="opacity:.75">No PR curve (no probabilities).</div>';
      }

      // 5) Calibration
      if (data.curves && data.curves.calibration){
        const diag={x:[0,1], y:[0,1], type:'scatter', mode:'lines', name:'Perfect', line:{dash:'dot'}};
        const curve={x:data.curves.calibration.mean_pred, y:data.curves.calibration.frac_pos, type:'scatter', mode:'lines+markers', name:'Reliability'};
        Plotly.newPlot('calib-plot', [diag, curve],
          Object.assign({}, H.darkLayout, {title:`Calibration (Brier=${H.fmt(c.brier,4)})`, xaxis:{title:'Mean predicted prob'}, yaxis:{title:'Empirical fraction of positives'}}),
          {responsive:true});
      } else {
        document.getElementById('calib-plot').innerHTML = '<div style="opacity:.75">No calibration (no probabilities).</div>';
      }

      // 6) Confusion Matrix
      if (('tn' in c) && ('tp' in c)){
        const z = [[c.tn||0, c.fp||0],[c.fn||0, c.tp||0]];
        Plotly.newPlot('cm-plot', [{
          z, type:'heatmap', colorscale:'Blues',
          x:['Pred 0', 'Pred 1'], y:['True 0','True 1'], showscale:true
        }], Object.assign({}, H.darkLayout, {title:'Confusion Matrix', yaxis:{autorange:'reversed'}}), {responsive:true});
      } else {
        document.getElementById('cm-plot').innerHTML = '<div style="opacity:.75">No confusion matrix.</div>';
      }

      // 7) Return histogram
      if (data.ret_hist){
        const edges = data.ret_hist.edges, counts = data.ret_hist.counts;
        const centers = edges.slice(0,-1).map((e,i)=> (e + edges[i+1]) / 2);
        Plotly.newPlot('hist-plot', [{x:centers, y:counts, type:'bar', name:'ret'}],
          Object.assign({}, H.darkLayout, {title:'Future Return Distribution (Test 1/6)', xaxis:{title:'ret'}, yaxis:{title:'count'}}),
          {responsive:true});
      }

      H.setStatus('backtest-status','Done.','ok');
    }catch(err){
      H.setStatus('backtest-status',`Error: ${err.message}`,'err');
      console.error(err);
    }
  };
})(window.HFT);
