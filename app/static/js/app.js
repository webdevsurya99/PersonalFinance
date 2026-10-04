// FinMinimal Application Core JS

let categoryChartInstance = null;
let trendChartInstance = null;

// Initialize Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((reg) => console.log('FinMinimal Service Worker Registered:', reg.scope))
      .catch((err) => console.log('Service Worker registration failed:', err));
  });
}

// Request Notification Permission
async function requestNotificationPermission() {
  if (!('Notification' in window)) {
    showToast('Notifications are not supported in this browser.', 'warning');
    return;
  }

  const permission = await Notification.requestPermission();
  if (permission === 'granted') {
    showToast('🔔 Notifications enabled! You will receive due-date alerts.', 'success');
    // Trigger initial notification check
    fetch('/api/notifications/sync-reminders', { method: 'POST' });
  } else {
    showToast('Notification permission was denied.', 'warning');
  }
}

// Toast Notifications System
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const bgColors = {
    success: 'bg-emerald-600 text-white border-emerald-500',
    danger: 'bg-rose-600 text-white border-rose-500',
    warning: 'bg-amber-600 text-white border-amber-500',
    info: 'bg-slate-800 text-white border-slate-700'
  };

  toast.className = `flex items-center gap-3 px-4 py-3 rounded-2xl border shadow-2xl transition-all duration-300 transform translate-y-4 opacity-0 text-sm font-medium ${bgColors[type] || bgColors.info}`;
  toast.innerHTML = `
    <span class="flex-1">${message}</span>
    <button onclick="this.parentElement.remove()" class="opacity-70 hover:opacity-100 text-lg leading-none">&times;</button>
  `;

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-4', 'opacity-0');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Open Quick Log Modal
function openLogModal(defaultType = 'expense') {
  const modal = document.getElementById('log-transaction-modal');
  if (!modal) return;

  // Set type radio
  const expenseRadio = document.getElementById('modal-type-expense');
  const incomeRadio = document.getElementById('modal-type-income');
  if (defaultType === 'income' && incomeRadio) {
    incomeRadio.checked = true;
    onTransactionTypeChange('income');
  } else if (expenseRadio) {
    expenseRadio.checked = true;
    onTransactionTypeChange('expense');
  }

  modal.classList.remove('hidden');
  modal.classList.add('flex');
  document.body.style.overflow = 'hidden';

  // Focus amount input
  const amtInput = document.getElementById('modal-amount-input');
  if (amtInput) {
    setTimeout(() => amtInput.focus(), 100);
  }
}

function closeLogModal() {
  const modal = document.getElementById('log-transaction-modal');
  if (!modal) return;
  modal.classList.add('hidden');
  modal.classList.remove('flex');
  document.body.style.overflow = '';
}

// Handle transaction type switch in modal
function onTransactionTypeChange(type) {
  const catSelect = document.getElementById('modal-category-select');
  if (!catSelect) return;

  // Filter category options based on type
  const options = catSelect.querySelectorAll('option[data-type]');
  let firstValid = null;
  options.forEach((opt) => {
    if (opt.dataset.type === type) {
      opt.style.display = '';
      if (!firstValid) firstValid = opt.value;
    } else {
      opt.style.display = 'none';
    }
  });

  if (firstValid) {
    catSelect.value = firstValid;
  }
}

// Update Dashboard Charts via API
async function loadDashboardCharts(period, startDate = '', endDate = '') {
  try {
    const url = new URL('/api/dashboard/stats', credentials = window.location.origin);
    url.searchParams.set('period', period);
    if (startDate) url.searchParams.set('start_date', startDate);
    if (endDate) url.searchParams.set('end_date', endDate);

    const res = await fetch(url.toString(), {
      headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) return;

    const data = await res.json();
    renderCategoryChart(data.category_chart, data.currency_symbol);
    renderTrendChart(data.daily_chart, data.currency_symbol);

    // Update KPI numbers dynamically if elements exist
    const incEl = document.getElementById('kpi-total-income');
    const expEl = document.getElementById('kpi-total-expense');
    const savEl = document.getElementById('kpi-net-savings');
    const rateEl = document.getElementById('kpi-savings-rate');

    if (incEl) incEl.textContent = `${data.currency_symbol} ${Number(data.total_income).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
    if (expEl) expEl.textContent = `${data.currency_symbol} ${Number(data.total_expense).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
    if (savEl) savEl.textContent = `${data.currency_symbol} ${Number(data.net_savings).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
    if (rateEl) rateEl.textContent = `${data.savings_rate}%`;

  } catch (err) {
    console.error('Error updating charts:', err);
  }
}

// Render Doughnut Category Chart
function renderCategoryChart(catData, currencySymbol) {
  const canvas = document.getElementById('categoryExpenseChart');
  if (!canvas) return;

  if (categoryChartInstance) {
    categoryChartInstance.destroy();
  }

  if (!catData || !catData.labels || catData.labels.length === 0) {
    // Empty state
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const parent = canvas.parentElement;
    const noData = document.getElementById('no-cat-data-msg');
    if (noData) noData.style.display = 'block';
    canvas.style.display = 'none';
    return;
  }

  const noData = document.getElementById('no-cat-data-msg');
  if (noData) noData.style.display = 'none';
  canvas.style.display = 'block';

  const ctx = canvas.getContext('2d');
  categoryChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: catData.labels,
      datasets: [{
        data: catData.data,
        backgroundColor: catData.colors,
        borderWidth: 0,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#94A3B8',
            font: { family: '-apple-system, BlinkMacSystemFont, sans-serif', size: 11 },
            boxWidth: 10,
            padding: 12
          }
        },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              const val = Number(ctx.parsed).toLocaleString('en-IN', { minimumFractionDigits: 2 });
              return ` ${ctx.label}: ${currencySymbol} ${val}`;
            }
          }
        }
      }
    }
  });
}

// Render Income vs Expense Trend Chart
function renderTrendChart(trendData, currencySymbol) {
  const canvas = document.getElementById('trendSpendingChart');
  if (!canvas) return;

  if (trendChartInstance) {
    trendChartInstance.destroy();
  }

  const ctx = canvas.getContext('2d');
  trendChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: trendData.labels || [],
      datasets: [
        {
          label: 'Income',
          data: trendData.income || [],
          backgroundColor: '#10B981',
          borderRadius: 6
        },
        {
          label: 'Expense',
          data: trendData.expense || [],
          backgroundColor: '#EF4444',
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#64748B', font: { size: 10 }, maxRotation: 45 }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: {
            color: '#64748B',
            font: { size: 10 },
            callback: (v) => `${currencySymbol}${v >= 1000 ? (v/1000).toFixed(0)+'k' : v}`
          }
        }
      },
      plugins: {
        legend: {
          position: 'top',
          labels: { color: '#94A3B8', boxWidth: 12 }
        },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              const val = Number(ctx.parsed.y).toLocaleString('en-IN', { minimumFractionDigits: 2 });
              return ` ${ctx.dataset.label}: ${currencySymbol} ${val}`;
            }
          }
        }
      }
    }
  });
}

// Notification Poller
async function updateNotificationBadge() {
  try {
    const res = await fetch('/api/notifications/unread-count');
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById('notification-badge');
      if (badge) {
        if (data.unread_count > 0) {
          badge.textContent = data.unread_count > 9 ? '9+' : data.unread_count;
          badge.classList.remove('hidden');
        } else {
          badge.classList.add('hidden');
        }
      }
    }
  } catch (e) {
    // Ignore network drop
  }
}

// Periodic check
setInterval(updateNotificationBadge, 45000);
document.addEventListener('DOMContentLoaded', () => {
  updateNotificationBadge();
});
