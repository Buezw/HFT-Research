// KPI coloring & rendering
(function(H){
  function getColor(metric, value){
    switch(metric){
      case 'Sharpe(step)':
      case 'Sharpe':
        if (value >= 1.0) return 'lime';
        if (value >= 0.2) return 'orange';
        return 'red';
      case 'Max Drawdown':
        if (value >= -0.05) return 'lime';
        if (value >= -0.20) return 'orange';
        return 'red';
      case 'Precision@thr':
        if (value >= 0.6) return 'lime';
        if (value >= 0.4) return 'orange';
        return 'red';
      case 'Recall@thr':
        if (value >= 0.8) return 'lime';
        if (value >= 0.6) return 'orange';
        return 'red';
      case 'F1@thr':
        if (value >= 0.6) return 'lime';
        if (value >= 0.4) return 'orange';
        return 'red';
      case 'AP':
        if (value >= 0.7) return 'lime';
        if (value >= 0.5) return 'orange';
        return 'red';
      case 'Brier':
        if (value < 0.1) return 'lime';
        if (value < 0.2) return 'orange';
        return 'red';
      default:
        return 'white';
    }
  }

  H.badge = (label, value)=>{
    const val = (typeof value === 'number') ? H.fmt(value, label==='Turnover'?1: (label==='Threshold'?3: (label==='Sharpe(step)'?3:4))) : String(value);
    const color = (typeof value === 'number') ? getColor(label, value) : 'white';
    return `<div class="metric" style="color:${color}"><small>${label}</small><div>${val}</div></div>`;
  };
})(window.HFT);
