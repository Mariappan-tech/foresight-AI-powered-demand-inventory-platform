/**
 * Project FORESIGHT — Interactive Dashboard Controller
 * Connects to Uvicorn ASGI Backend, renders dynamic Chart.js visualizations,
 * handles inventory triage actions and interactive What-If demand simulations.
 */

// Base API URL: Automatically routes to backend port 5000 if frontend is opened via Live Server (port 5500) or file protocol
const API_BASE = (window.location.port === '5000' || (!window.location.port && window.location.protocol.startsWith('http') && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'))
  ? ''
  : 'http://127.0.0.1:5000';

// Theme State ('bw' = Black & White Luxury Noir, 'neon' = Color)
let currentTheme = localStorage.getItem('foresight_theme') || 'bw';

// Currency State & Settings ($ USD and ₹ INR)
let currentCurrency = localStorage.getItem('foresight_currency') || 'USD';
const USD_TO_INR = 83.5; // Standard exchange rate (1 USD = ₹83.50)

function formatCurrency(amountUSD, showDecimals = true) {
  if (amountUSD === null || amountUSD === undefined || isNaN(amountUSD)) return '--';
  const num = Number(amountUSD);
  if (currentCurrency === 'INR') {
    const valINR = num * USD_TO_INR;
    return `₹${valINR.toLocaleString('en-IN', {
      minimumFractionDigits: showDecimals ? 2 : 0,
      maximumFractionDigits: showDecimals ? 2 : 0
    })}`;
  } else {
    return `$${num.toLocaleString('en-US', {
      minimumFractionDigits: showDecimals ? 2 : 0,
      maximumFractionDigits: showDecimals ? 2 : 0
    })}`;
  }
}

// Global State
let globalInventory = [];
let globalForecast = [];
let globalHistory = [];
let globalKPIData = null;
let lastSimulationResult = null;
let demandChart = null;
let inventoryChart = null;
let categoryChart = null;

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initThemeUI();
  initCurrencyUI();
  initApp();
  setupEventListeners();
});

function initThemeUI() {
  if (currentTheme === 'bw') {
    document.body.classList.add('theme-bw');
  } else {
    document.body.classList.remove('theme-bw');
  }
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.theme === currentTheme);
  });
}

function setTheme(theme) {
  if (currentTheme === theme) return;
  currentTheme = theme;
  localStorage.setItem('foresight_theme', theme);

  if (theme === 'bw') {
    document.body.classList.add('theme-bw');
  } else {
    document.body.classList.remove('theme-bw');
  }

  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.theme === theme);
  });

  // Re-render charts with the new theme colors
  const currentSku = document.getElementById('chartSkuSelect') ? document.getElementById('chartSkuSelect').value : 'ALL';
  renderDemandForecastChart(currentSku);
  if (globalInventory && globalInventory.length) {
    renderInventoryComparisonChart(globalInventory);
    renderCategoryDoughnut(globalInventory);
  }

  showToast(`Theme switched to ${theme === 'bw' ? 'Black & White Monochrome' : 'Vibrant Color'}`, 'info');
}

function updateSkuDropdownPrices() {
  const select = document.getElementById('sim-sku');
  if (!select) return;
  const labels = {
    'SKU_REORDER': `SKU_REORDER (Furniture - ${formatCurrency(249.99)})`,
    'SKU_CLEAR': `SKU_CLEAR (Decor - ${formatCurrency(29.99)})`,
    'SKU_WATCH': `SKU_WATCH (Textiles - ${formatCurrency(89.99)})`,
    'SKU_HEALTHY': `SKU_HEALTHY (Lighting - ${formatCurrency(79.99)})`
  };
  Array.from(select.options).forEach(opt => {
    if (labels[opt.value]) {
      opt.textContent = labels[opt.value];
    }
  });
}

function initCurrencyUI() {
  document.querySelectorAll('.curr-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.currency === currentCurrency);
  });
  const priceLabel = document.getElementById('sim-price-label');
  if (priceLabel) {
    priceLabel.textContent = `Simulated Price (${currentCurrency === 'INR' ? '₹ INR' : '$ USD'})`;
  }
  const priceInput = document.getElementById('sim-price');
  if (priceInput) {
    priceInput.value = currentCurrency === 'INR' ? (249.99 * USD_TO_INR).toFixed(2) : '249.99';
  }
  updateSkuDropdownPrices();
}

function setCurrency(currency) {
  if (currentCurrency === currency) return;
  const prevCurrency = currentCurrency;
  currentCurrency = currency;
  localStorage.setItem('foresight_currency', currency);

  // Update button active state
  document.querySelectorAll('.curr-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.currency === currency);
  });

  // Update input label and value in simulator
  const priceInput = document.getElementById('sim-price');
  const priceLabel = document.getElementById('sim-price-label');
  if (priceLabel) {
    priceLabel.textContent = `Simulated Price (${currency === 'INR' ? '₹ INR' : '$ USD'})`;
  }

  if (priceInput && priceInput.value) {
    const currentVal = parseFloat(priceInput.value);
    if (!isNaN(currentVal)) {
      if (currency === 'INR' && prevCurrency === 'USD') {
        priceInput.value = (currentVal * USD_TO_INR).toFixed(2);
      } else if (currency === 'USD' && prevCurrency === 'INR') {
        priceInput.value = (currentVal / USD_TO_INR).toFixed(2);
      }
    }
  }

  // Update dropdown SKU prices
  updateSkuDropdownPrices();

  // Re-render KPI Inventory Value
  if (globalKPIData) {
    document.getElementById('kpi-inventory-val').textContent = formatCurrency(globalKPIData.total_stock_value_usd, false);
  }

  // Re-render Inventory Table & Category Chart
  if (globalInventory && globalInventory.length) {
    renderInventoryTable(globalInventory);
    renderCategoryDoughnut(globalInventory);
  }

  // Re-render Simulation Output
  if (lastSimulationResult) {
    document.getElementById('res-revenue').textContent = formatCurrency(lastSimulationResult.estimated_revenue);
    document.getElementById('res-profit').textContent = formatCurrency(lastSimulationResult.estimated_profit);
  } else {
    runSimulation();
  }

  showToast(`Currency switched to ${currency === 'INR' ? 'Indian Rupee (₹)' : 'US Dollar ($)'}`, 'info');
}

async function initApp() {
  showToast('Connecting to Project FORESIGHT AI Engine...', 'info');
  let failures = 0;
  const safeFetch = async (fn, name) => {
    try {
      await fn();
    } catch (err) {
      console.error(`Failed to load ${name}:`, err);
      failures++;
    }
  };

  await Promise.all([
    safeFetch(fetchKPIs, 'KPIs'),
    safeFetch(fetchInventoryData, 'Inventory'),
    safeFetch(fetchForecastData, 'Forecast'),
    safeFetch(fetchSalesHistory, 'SalesHistory'),
    safeFetch(fetchModelMetrics, 'ModelMetrics')
  ]);

  if (failures >= 3) {
    showToast('Backend connection failed! Ensure app.py is running on http://127.0.0.1:5000', 'danger');
    const badge = document.querySelector('.status-badge');
    if (badge) {
      badge.innerHTML = '<span class="pulse-dot" style="background:#ef4444;box-shadow:0 0 10px #ef4444;"></span><span style="color:#ef4444;">Engine Disconnected</span>';
    }
  } else {
    runSimulation();
    showToast('AI Intelligence Platform Online & Synced!', 'success');
  }
}

// -------------------------------------------------------------
// 1. Fetch High-Level Executive KPIs
// -------------------------------------------------------------
async function fetchKPIs() {
  try {
    const res = await fetch(`${API_BASE}/api/kpis`);
    if (!res.ok) throw new Error('Failed to load KPIs');
    const data = await res.json();
    globalKPIData = data;

    document.getElementById('kpi-accuracy').textContent = `${data.forecast_accuracy_pct}%`;
    document.getElementById('kpi-accuracy-sub').textContent = `WAPE: ${data.forecast_wape_pct}% | R²: ${data.model_r2_score}`;
    
    document.getElementById('kpi-stockout').textContent = data.stockout_risk_count;
    document.getElementById('kpi-overstock').textContent = data.overstock_risk_count;
    document.getElementById('kpi-pipeline').textContent = `${data.total_stock_on_hand + data.total_stock_on_order} units`;
    document.getElementById('kpi-inventory-val').textContent = formatCurrency(data.total_stock_value_usd, false);
    document.getElementById('kpi-watch').textContent = data.watch_skus_count;
  } catch (err) {
    console.error('KPI error:', err);
  }
}

// -------------------------------------------------------------
// 2. Fetch Detailed Inventory Intelligence Table
// -------------------------------------------------------------
async function fetchInventoryData() {
  try {
    const res = await fetch(`${API_BASE}/api/inventory`);
    if (!res.ok) throw new Error('Failed to load inventory');
    const json = await res.json();
    globalInventory = json.data;

    renderInventoryTable(globalInventory);
    renderInventoryComparisonChart(globalInventory);
    renderCategoryDoughnut(globalInventory);
  } catch (err) {
    console.error('Inventory error:', err);
  }
}

function renderInventoryTable(items) {
  const tbody = document.getElementById('inventory-table-body');
  tbody.innerHTML = '';

  items.forEach(sku => {
    const tr = document.createElement('tr');

    let statusPill = '';
    let actionBtn = '';
    let barColor = 'fill-success';

    if (sku.inventory_status === 'STOCKOUT_RISK') {
      statusPill = `<span class="status-pill stockout"><i class="fa-solid fa-triangle-exclamation"></i> Critical Reorder</span>`;
      actionBtn = `<button class="action-btn reorder" onclick="triggerAction('PO', '${sku.sku_id}', ${sku.reorder_point})"><i class="fa-solid fa-bolt"></i> Order Stock</button>`;
      barColor = 'fill-danger';
    } else if (sku.inventory_status === 'OVERSTOCK_RISK') {
      statusPill = `<span class="status-pill overstock"><i class="fa-solid fa-box-archive"></i> Overstock Excess</span>`;
      actionBtn = `<button class="action-btn promo" onclick="triggerAction('PROMO', '${sku.sku_id}')"><i class="fa-solid fa-tags"></i> Flash Promo</button>`;
      barColor = 'fill-warning';
    } else if (sku.inventory_status === 'EXPEDITE_PO' || sku.inventory_status === 'VOLATILE_WATCH') {
      statusPill = `<span class="status-pill watch"><i class="fa-solid fa-eye"></i> Volatile Watch</span>`;
      actionBtn = `<button class="action-btn expedite" onclick="triggerAction('EXPEDITE', '${sku.sku_id}')"><i class="fa-solid fa-truck-fast"></i> Expedite PO</button>`;
      barColor = 'fill-violet';
    } else {
      statusPill = `<span class="status-pill healthy"><i class="fa-solid fa-circle-check"></i> Balanced</span>`;
      actionBtn = `<button class="action-btn ok" onclick="triggerAction('INFO', '${sku.sku_id}')"><i class="fa-solid fa-check"></i> Optimal</button>`;
    }

    // DOS fill calculation (capped at 100% for bar)
    const dosPct = Math.min(100, (sku.days_of_supply / 60) * 100);

    tr.innerHTML = `
      <td>
        <div class="sku-name">${sku.sku_id}</div>
        <div class="category-tag">${sku.category}</div>
      </td>
      <td>
        <strong>${formatCurrency(sku.selling_price)}</strong>
        <div class="category-tag">Cost: ${formatCurrency(sku.unit_cost)} (${sku.margin_pct}%)</div>
      </td>
      <td>
        <strong>${sku.avg_daily_sales.toFixed(1)}</strong> / day
        <div class="category-tag">Std: ±${sku.std_daily_sales.toFixed(1)}</div>
      </td>
      <td>
        <span style="font-size: 15px; font-weight:700;">${sku.current_stock_on_hand}</span>
        ${sku.current_stock_on_order > 0 ? `<span style="color:#a78bfa; font-size:12px; margin-left:4px;">(+${sku.current_stock_on_order} on order)</span>` : ''}
      </td>
      <td>
        <strong>${sku.days_of_supply} days</strong>
        <div class="dos-bar-wrap">
          <div class="dos-bar-fill ${barColor}" style="width: ${dosPct}%"></div>
        </div>
      </td>
      <td>
        <div>Safety: <strong>${sku.safety_stock}</strong></div>
        <div>ROP: <strong style="color: #38bdf8;">${sku.reorder_point}</strong></div>
      </td>
      <td>${statusPill}</td>
      <td>${actionBtn}</td>
    `;
    tbody.appendChild(tr);
  });
}

// -------------------------------------------------------------
// 3. Fetch Forecast & Sales History
// -------------------------------------------------------------
async function fetchForecastData() {
  try {
    const res = await fetch(`${API_BASE}/api/forecast?days=14`);
    if (!res.ok) throw new Error('Failed to load forecast');
    const json = await res.json();
    globalForecast = json.data;
  } catch (err) {
    console.error('Forecast error:', err);
    throw err;
  }
}

async function fetchSalesHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/sales-history?days=30`);
    if (!res.ok) throw new Error('Failed to load history');
    const json = await res.json();
    globalHistory = json.data;

    renderDemandForecastChart('ALL');
  } catch (err) {
    console.error('History error:', err);
    throw err;
  }
}

// -------------------------------------------------------------
// 4. Render Main Multi-Step Demand Chart
// -------------------------------------------------------------
function renderDemandForecastChart(selectedSku) {
  const ctx = document.getElementById('demandForecastChart').getContext('2d');

  // Filter datasets
  let histData = globalHistory;
  let fcastData = globalForecast;

  if (selectedSku !== 'ALL') {
    histData = histData.filter(d => d.sku_id === selectedSku);
    fcastData = fcastData.filter(d => d.sku_id === selectedSku);
  }

  // Aggregate by date
  const dateMap = new Map();

  histData.forEach(d => {
    if (!dateMap.has(d.date)) dateMap.set(d.date, { date: d.date, actual: 0, forecast: null });
    dateMap.get(d.date).actual += d.sales_units;
  });

  fcastData.forEach(d => {
    if (!dateMap.has(d.date)) dateMap.set(d.date, { date: d.date, actual: null, forecast: 0 });
    dateMap.get(d.date).forecast = (dateMap.get(d.date).forecast || 0) + d.predicted_demand;
  });

  const sortedDates = Array.from(dateMap.values()).sort((a, b) => new Date(a.date) - new Date(b.date));

  // Connect last actual point to first forecast point for seamless curve
  const labels = sortedDates.map(d => d.date.slice(5)); // MM-DD
  const actualSeries = sortedDates.map(d => d.actual);
  const forecastSeries = sortedDates.map(d => d.forecast);

  // Smooth connector
  const lastActualIdx = actualSeries.map((v, i) => v !== null ? i : -1).filter(i => i !== -1).pop();
  if (lastActualIdx !== undefined && forecastSeries[lastActualIdx + 1] !== undefined) {
    forecastSeries[lastActualIdx] = actualSeries[lastActualIdx];
  }

  if (demandChart) demandChart.destroy();

  const isBw = currentTheme === 'bw';
  const histBorder = isBw ? '#64748b' : '#38bdf8';
  const histBg = isBw ? 'rgba(100, 116, 139, 0.08)' : 'rgba(56, 189, 248, 0.1)';
  const fcastBorder = isBw ? '#000000' : '#a78bfa';
  const fcastBg = isBw ? 'rgba(0, 0, 0, 0.06)' : 'rgba(167, 139, 250, 0.12)';
  const tooltipTitle = isBw ? '#ffffff' : '#38bdf8';
  const tooltipBorder = isBw ? '#000000' : 'rgba(56, 189, 248, 0.3)';

  demandChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Historical Actual Sales',
          data: actualSeries,
          borderColor: histBorder,
          backgroundColor: histBg,
          fill: true,
          tension: 0.35,
          borderWidth: 2.5,
          pointRadius: 2.5,
          pointHoverRadius: 6
        },
        {
          label: 'AI Forward Demand Forecast (14-Day)',
          data: forecastSeries,
          borderColor: fcastBorder,
          backgroundColor: fcastBg,
          borderDash: [5, 5],
          fill: true,
          tension: 0.35,
          borderWidth: 2.5,
          pointRadius: 3.5,
          pointHoverRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          labels: { color: isBw ? '#000000' : '#94a3b8', font: { family: 'Plus Jakarta Sans', size: 12, weight: isBw ? 'bold' : 'normal' } }
        },
        tooltip: {
          backgroundColor: isBw ? 'rgba(0, 0, 0, 0.92)' : 'rgba(15, 23, 42, 0.95)',
          titleColor: tooltipTitle,
          bodyColor: '#ffffff',
          borderColor: tooltipBorder,
          borderWidth: 1,
          padding: 12
        }
      },
      scales: {
        x: {
          grid: { color: isBw ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: isBw ? '#000000' : '#64748b', maxTicksLimit: 12 }
        },
        y: {
          grid: { color: isBw ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: isBw ? '#000000' : '#64748b' }
        }
      }
    }
  });
}

// -------------------------------------------------------------
// 5. Render Inventory vs ROP Bar Chart
// -------------------------------------------------------------
function renderInventoryComparisonChart(inventory) {
  const ctx = document.getElementById('inventoryBarChart').getContext('2d');

  const skus = inventory.map(i => i.sku_id.replace('SKU_', ''));
  const stockOnHand = inventory.map(i => i.current_stock_on_hand);
  const reorderPoints = inventory.map(i => i.reorder_point);
  const safetyStock = inventory.map(i => i.safety_stock);

  if (inventoryChart) inventoryChart.destroy();

  const isBw = currentTheme === 'bw';
  const colorStock = isBw ? '#000000' : '#38bdf8';
  const colorRop = isBw ? '#475569' : '#f43f5e';
  const colorSafety = isBw ? '#94a3b8' : '#10b981';

  inventoryChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: skus,
      datasets: [
        {
          label: 'Current Stock on Hand',
          data: stockOnHand,
          backgroundColor: colorStock,
          borderRadius: 6
        },
        {
          label: 'Reorder Point (ROP)',
          data: reorderPoints,
          backgroundColor: colorRop,
          borderRadius: 6
        },
        {
          label: 'Safety Stock Buffer',
          data: safetyStock,
          backgroundColor: colorSafety,
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: isBw ? '#000000' : '#94a3b8', font: { family: 'Plus Jakarta Sans', size: 11, weight: isBw ? 'bold' : 'normal' } }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: isBw ? '#000000' : '#94a3b8', font: { weight: 'bold' } }
        },
        y: {
          grid: { color: isBw ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: isBw ? '#000000' : '#64748b' }
        }
      }
    }
  });
}

// -------------------------------------------------------------
// 6. Category Revenue Doughnut Chart
// -------------------------------------------------------------
function renderCategoryDoughnut(inventory) {
  const ctx = document.getElementById('categoryDoughnutChart').getContext('2d');

  const categories = inventory.map(i => i.category);
  const totalValues = inventory.map(i => i.current_stock_on_hand * i.unit_cost);

  if (categoryChart) categoryChart.destroy();

  const isBw = currentTheme === 'bw';
  const doughnutColors = isBw
    ? ['#000000', '#334155', '#64748b', '#94a3b8']
    : ['#f59e0b', '#10b981', '#f43f5e', '#8b5cf6'];

  categoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: categories,
      datasets: [{
        data: totalValues,
        backgroundColor: doughnutColors,
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: isBw ? '#000000' : '#94a3b8', font: { family: 'Plus Jakarta Sans', size: 11, weight: isBw ? 'bold' : 'normal' }, boxWidth: 12 }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return ` ${context.label}: ${formatCurrency(context.raw, false)}`;
            }
          }
        }
      },
      cutout: '70%'
    }
  });
}

// -------------------------------------------------------------
// 7. What-If Scenario Simulator Logic
// -------------------------------------------------------------
async function runSimulation() {
  const sku_id = document.getElementById('sim-sku').value;
  const promotion_active = parseInt(document.querySelector('.toggle-btn[data-type="promo"].active').dataset.val);
  const is_holiday = parseInt(document.querySelector('.toggle-btn[data-type="holiday"].active').dataset.val);
  const day_of_week = parseInt(document.getElementById('sim-dow').value);
  const rawPrice = parseFloat(document.getElementById('sim-price').value) || null;
  // Convert custom_price to USD for model inference if current currency is INR
  const custom_price = (rawPrice !== null && currentCurrency === 'INR') ? (rawPrice / USD_TO_INR) : rawPrice;

  try {
    const res = await fetch(`${API_BASE}/api/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sku_id,
        promotion_active,
        is_holiday,
        day_of_week,
        selling_price: custom_price
      })
    });
    if (!res.ok) throw new Error('Simulation failed');
    const data = await res.json();
    lastSimulationResult = data;

    document.getElementById('res-demand').textContent = `${data.predicted_demand_units} units`;
    document.getElementById('res-revenue').textContent = formatCurrency(data.estimated_revenue);
    document.getElementById('res-profit').textContent = formatCurrency(data.estimated_profit);

    const marginRate = data.estimated_revenue > 0 ? ((data.estimated_profit / data.estimated_revenue) * 100).toFixed(1) : 0;
    document.getElementById('res-margin').textContent = `${marginRate}% Margin`;
  } catch (err) {
    console.error('Simulation error:', err);
  }
}

// -------------------------------------------------------------
// 8. Feature Importance & Model Benchmark
// -------------------------------------------------------------
async function fetchModelMetrics() {
  try {
    const res = await fetch(`${API_BASE}/api/model-metrics`);
    if (!res.ok) throw new Error('Failed to load metrics');
    const data = await res.json();

    document.getElementById('champ-model-name').textContent = data.champion_model;

    // Feature importance bars
    const featContainer = document.getElementById('feature-importance-list');
    featContainer.innerHTML = '';

    const topFeatures = data.feature_importance || [];
    topFeatures.forEach(f => {
      const pct = (f.importance * 100).toFixed(1);
      const item = document.createElement('div');
      item.className = 'feat-item';
      item.innerHTML = `
        <div class="feat-header">
          <span style="color: #e2e8f0; font-family: var(--font-mono);">${f.feature}</span>
          <span style="color: #38bdf8;">${pct}%</span>
        </div>
        <div class="feat-bar-bg">
          <div class="feat-bar-fill" style="width: ${Math.min(100, pct * 3)}%"></div>
        </div>
      `;
      featContainer.appendChild(item);
    });

    // Populate benchmark table
    const benchBody = document.getElementById('benchmark-table-body');
    benchBody.innerHTML = '';
    (data.benchmark || []).forEach(b => {
      const tr = document.createElement('tr');
      const isChamp = b.Model.includes(data.champion_model) || b.Model.includes('Tuned Random Forest');
      tr.innerHTML = `
        <td><strong>${b.Model}</strong> ${isChamp ? '<span class="status-pill healthy" style="margin-left:6px; font-size:10px;">Champion</span>' : ''}</td>
        <td>${b['Test MAE']}</td>
        <td>${b['Test RMSE']}</td>
        <td style="color:${isChamp ? '#10b981' : '#94a3b8'}; font-weight:700;">${b['Test WAPE (%)']}%</td>
        <td>${b['Test R2']}</td>
      `;
      benchBody.appendChild(tr);
    });

  } catch (err) {
    console.error('Metrics error:', err);
  }
}

// -------------------------------------------------------------
// 9. Interactive Action Triggering & Toasts
// -------------------------------------------------------------
function triggerAction(type, skuId, qty = 50) {
  if (type === 'PO') {
    showToast(`⚡ Purchase Order PO-${Date.now().toString().slice(-4)} created: ${qty} units for ${skuId}`, 'success');
  } else if (type === 'PROMO') {
    showToast(`🏷️ Clearance 20% discount campaign scheduled for ${skuId}!`, 'warning');
  } else if (type === 'EXPEDITE') {
    showToast(`🚚 Expedite alert dispatched to freight carrier for ${skuId}!`, 'info');
  } else {
    showToast(`✅ ${skuId} inventory is healthy and within optimal parameters.`, 'success');
  }
}

function showToast(message, type = 'info') {
  const toast = document.getElementById('app-toast');
  const toastMsg = document.getElementById('toast-msg');
  const toastIcon = document.getElementById('toast-icon');

  toastMsg.textContent = message;

  if (type === 'success') {
    toastIcon.className = 'fa-solid fa-circle-check';
    toast.style.borderColor = '#10b981';
  } else if (type === 'warning') {
    toastIcon.className = 'fa-solid fa-triangle-exclamation';
    toast.style.borderColor = '#f59e0b';
  } else if (type === 'danger' || type === 'error') {
    toastIcon.className = 'fa-solid fa-circle-xmark';
    toast.style.borderColor = '#ef4444';
  } else {
    toastIcon.className = 'fa-solid fa-circle-info';
    toast.style.borderColor = '#06b6d4';
  }

  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

// -------------------------------------------------------------
// 10. Event Listeners Setup
// -------------------------------------------------------------
function setupEventListeners() {
  // Chart SKU selector
  document.getElementById('chartSkuSelect').addEventListener('change', (e) => {
    renderDemandForecastChart(e.target.value);
  });

  // Simulator SKU selector
  document.getElementById('sim-sku').addEventListener('change', (e) => {
    const sku = globalInventory.find(i => i.sku_id === e.target.value);
    if (sku) {
      const priceVal = currentCurrency === 'INR'
        ? (sku.selling_price * USD_TO_INR).toFixed(2)
        : sku.selling_price.toFixed(2);
      document.getElementById('sim-price').value = priceVal;
    }
    runSimulation();
  });

  // Currency Switcher buttons
  document.querySelectorAll('.curr-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const targetBtn = e.target.closest('.curr-btn');
      if (targetBtn) {
        setCurrency(targetBtn.dataset.currency);
      }
    });
  });

  // Theme Switcher buttons (Color vs Black & White)
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const targetBtn = e.target.closest('.theme-btn');
      if (targetBtn) {
        setTheme(targetBtn.dataset.theme);
      }
    });
  });

  // Simulator toggles
  document.querySelectorAll('.toggle-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const type = e.target.dataset.type;
      document.querySelectorAll(`.toggle-btn[data-type="${type}"]`).forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      runSimulation();
    });
  });

  // Simulator Day of week & Price inputs
  document.getElementById('sim-dow').addEventListener('change', runSimulation);
  document.getElementById('sim-price').addEventListener('input', runSimulation);

  // Refresh button
  document.getElementById('btn-refresh').addEventListener('click', () => {
    initApp();
  });

  // Export CSV button
  document.getElementById('btn-export').addEventListener('click', () => {
    if (!globalForecast.length) return;
    const header = Object.keys(globalForecast[0]).join(',');
    const rows = globalForecast.map(f => Object.values(f).join(','));
    const csvContent = 'data:text/csv;charset=utf-8,' + [header, ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'foresight_14day_demand_forecast.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Exported 14-day demand forecast to CSV!', 'success');
  });

  // Smooth scroll for nav items
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
      link.classList.add('active');
      const targetId = link.getAttribute('href').substring(1);
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });
}
