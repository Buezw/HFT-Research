// Factors: load & show
(function(H){
  H.loadFactors = async function(){
    const res = await fetch('/api/factors'); const data = await res.json();
    const c = document.getElementById('factor-categories'); c.innerHTML = '';
    for (const [cat,factors] of Object.entries(data)){
      const card = document.createElement('div');
      card.className = 'card';
      card.style.cursor = 'pointer';
      card.innerHTML = `<b>${cat}</b><br><small class="muted">探索 →</small>`;
      card.onclick = ()=> H.showFactorList(cat, factors);
      c.appendChild(card);
    }
    H._factorsData = data;
  };

  H.showFactorList = function(cat, factors){
    const c = document.getElementById('factor-categories');
    c.innerHTML = `<h4 style="margin:6px 0 10px 0;">${cat}</h4>`;
    for (const [name, meta] of Object.entries(factors)){
      const item = document.createElement('div');
      item.style = 'padding:8px; cursor:pointer; color:#0af; border-bottom:1px solid #333;';
      item.textContent = name;
      item.onclick = ()=> H.showFactor(name, meta);
      c.appendChild(item);
    }
  };

  H.showFactor = async function(name, meta){
    H.selectedFactor = name;
    document.getElementById('factor-title').textContent = name;
    document.getElementById('factor-desc').textContent = meta.desc || '';
    document.getElementById('factor-formula').textContent = meta.formula || '';
    document.getElementById('factor-explanation').textContent = meta.explanation || '';

    const res = await fetch(`/api/compute?factor=${encodeURIComponent(name)}`);
    const data = await res.json();
    Plotly.newPlot('plot', [{x:data.x, y:data.y, type:'scatter', mode:'lines'}],
      Object.assign({}, H.darkLayout, {title:`${name} over time`}), {responsive:true});
  };
})(window.HFT);
