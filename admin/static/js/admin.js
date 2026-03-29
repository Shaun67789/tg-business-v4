/**
 * TG Business Admin — JavaScript
 * Toast system, shared UI helpers, mobile sidebar
 */

// ── Toast System ──────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ── Mobile Sidebar Toggle ─────────────────────────────────────────
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('sidebar');

if (sidebarToggle && sidebar) {
  sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  // Close on outside click (mobile)
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 &&
        !sidebar.contains(e.target) &&
        sidebar.classList.contains('open')) {
      sidebar.classList.remove('open');
    }
  });
}

// ── Table Row Highlights ──────────────────────────────────────────
document.querySelectorAll('.data-table tbody tr').forEach(row => {
  row.addEventListener('mouseenter', () => row.style.background = 'rgba(255,255,255,0.025)');
  row.addEventListener('mouseleave', () => row.style.background = '');
});

// ── Auto-resize textareas ─────────────────────────────────────────
document.querySelectorAll('textarea.form-input').forEach(ta => {
  ta.addEventListener('input', () => {
    ta.style.height = 'auto';
    ta.style.height = ta.scrollHeight + 'px';
  });
});

// ── Confirm helper ────────────────────────────────────────────────
function confirmAction(msg) {
  return window.confirm(msg);
}

// ── Number formatter ─────────────────────────────────────────────
function formatNumber(n) {
  return new Intl.NumberFormat().format(n);
}

// ── Date formatter ────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}
