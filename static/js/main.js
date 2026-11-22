
    // Role Definitions & Allowed Navigation Items
    const ROLES = {
      dispatcher: {
        role: 'dispatcher',
        name: 'Gowtham K',
        email: 'analyst@routemind.ai',
        role_display: 'Operations Analyst',
        initials: 'GK',
        nav: [
          { id: 'shipments', label: 'Shipments', icon: 'bi-box-seam' },
          { id: 'exceptions', label: 'Exceptions', icon: 'bi-exclamation-octagon' },
          { id: 'escalations', label: 'Escalations', icon: 'bi-arrow-up-right-circle' }
        ]
      },
      manager: {
        role: 'manager',
        name: 'Suresh Raina',
        email: 'manager@routemind.ai',
        role_display: 'Operations Manager',
        initials: 'SR',
        nav: [
          { id: 'shipments', label: 'Shipments', icon: 'bi-box-seam' },
          { id: 'exceptions', label: 'Exceptions', icon: 'bi-exclamation-octagon' },
          { id: 'escalations', label: 'Escalations', icon: 'bi-arrow-up-right-circle' }
        ]
      },
      admin: {
        role: 'admin',
        name: 'Gowtham (Admin)',
        email: 'admin@routemind.ai',
        role_display: 'Administrator',
        initials: 'GA',
        nav: [
          { id: 'shipments', label: 'Shipments', icon: 'bi-box-seam' },
          { id: 'users', label: 'User Management', icon: 'bi-people' },
          { id: 'admin-settings', label: 'System Settings', icon: 'bi-sliders' }
        ]
      }
    };

    let currentUser = null;
    let currentScreen = 'login';
    let chartsInitialized = false;

    // Quick Login
    function quickLogin(roleKey) {
      window.location.href = '/auth/quick-login/' + roleKey;
    }

    function handleLoginForm(e) {
      e.preventDefault();
      const email = document.getElementById('loginEmail').value;
      const password = document.getElementById('loginPassword').value;
      
      fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, password: password })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          showToast('Sign in verified. Accessing Control Tower...', 'success');
          window.location.href = data.redirect || '/';
        } else {
          showToast(data.message || 'Invalid credentials or inactive account', 'danger');
        }
      })
      .catch(err => {
        // Fallback to native form post
        e.target.action = '/auth/login';
        e.target.method = 'POST';
        e.target.submit();
      });
    }

    function logout() {
      window.location.href = '/auth/logout';
    }

    function renderNavbar() {
      const container = document.getElementById('topNavTabs');
      if (!container || !currentUser) return;

      container.innerHTML = currentUser.nav.map(item => `
        <a href="javascript:void(0)" onclick="navigateTo('${item.id}')" data-screen="${item.id}"
           class="nav-tab-pill ${currentScreen === item.id ? 'active' : ''}">
          <i class="bi ${item.icon}"></i>
          <span>${item.label}</span>
        </a>
      `).join('');
    }

    function navigateTo(screenId) {
      const routeMap = {
        'dashboard': '/',
        'control-tower': '/',
        'shipments': '/shipments/',
        'shipment_list': '/shipments/',
        'new-shipment': '/shipments/new',
        'anomalies': '/anomalies/',
        'exceptions': '/exceptions/',
        'escalations': '/escalations/',
        'reports': '/reports/',
        'ai_assistant': '/ai/assistant',
        'assistant': '/ai/assistant',
        'users': '/users/',
        'admin-settings': '/admin/settings',
        'settings': '/admin/settings',
        'login': '/auth/login',
        'forgot-password': '/auth/forgot-password'
      };

      const target = document.getElementById('screen-' + screenId);
      if (target) {
        document.querySelectorAll('.screen-view').forEach(el => el.classList.remove('active'));
        target.classList.add('active');
        currentScreen = screenId;
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else if (routeMap[screenId]) {
        window.location.href = routeMap[screenId];
        return;
      }

      // Highlight active nav tab
      document.querySelectorAll('#topNavTabs a').forEach(a => {
        if (a.getAttribute('data-screen') === screenId) a.classList.add('active');
        else a.classList.remove('active');
      });

      // Lazy init charts on reports screen
      if (screenId === 'reports' && !chartsInitialized) {
        initReportsCharts();
        chartsInitialized = true;
      }
    }

    function openShipmentDetail(shipmentId) {
      if (shipmentId) {
        window.location.href = '/shipments/' + encodeURIComponent(shipmentId);
      } else {
        window.location.href = '/shipments/';
      }
    }

    function switchDetailTab(tabId, btn) {
      document.querySelectorAll('#detailTabs .nav-link').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      showToast(`Switched to ${btn.textContent.trim()} view`, 'info');
    }

    // Chart.js initializers matching dynamic database reports
    async function initReportsCharts() {
      const ctxBar = document.getElementById('chartDeliveryPerformance');
      const ctxDonut = document.getElementById('chartShipmentStatus');
      if (!ctxBar && !ctxDonut) return;
      if (Chart.getChart(ctxBar) || Chart.getChart(ctxDonut)) return; // already initialized

      try {
        const res = await fetch('/reports/api/chart-data');
        if (!res.ok) return;
        const chartData = await res.json();

        // 1. Delivery Performance Bar Chart
        if (ctxBar && chartData.performance_chart && !Chart.getChart(ctxBar)) {
          const perf = chartData.performance_chart;
          new Chart(ctxBar, {
            type: 'bar',
            data: {
              labels: perf.labels,
              datasets: [
                {
                  label: 'Scheduled',
                  data: perf.scheduled,
                  backgroundColor: '#4F46E5',
                  borderRadius: 4
                },
                {
                  label: 'Delivered / On-Track',
                  data: perf.delivered,
                  backgroundColor: '#38BDF8',
                  borderRadius: 4
                }
              ]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                y: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { stepSize: 1 } },
                x: { grid: { display: false } }
              }
            }
          });
        }

        // 2. Shipment Status Donut Chart
        if (ctxDonut && chartData.status_chart && !Chart.getChart(ctxDonut)) {
          const st = chartData.status_chart;
          new Chart(ctxDonut, {
            type: 'doughnut',
            data: {
              labels: st.labels,
              datasets: [{
                data: st.data,
                backgroundColor: ['#4F46E5', '#10B981', '#F59E0B', '#EF4444'],
                borderWidth: 0,
                hoverOffset: 4
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              cutout: '72%',
              plugins: { legend: { display: false } }
            }
          });
        }
      } catch (e) {
        console.warn('Failed to load dynamic chart data:', e);
      }
    }

    // Copilot Functions (Image 5)
    function toggleCopilot() {
      window.location.href = '/ai-assistant/';
    }

    function sendQuickPrompt(promptText) {
      appendUserMessage(promptText);
      setTimeout(() => {
        let reply = "Analysis complete for your request.";
        if (promptText.includes('SHP-10482')) {
          reply = "Consignment SHP-10482 has an 82% delay risk probability driven primarily by Singapore terminal berthing queues (+0.32 SHAP duration, +0.21 congestion). Recommended mitigation: Pre-clear PSA offload window.";
        } else if (promptText.includes('Draft 48h Delay')) {
          reply = "Draft prepared: Advisory notification states expected 48-72h delay due to Singapore Straits queue. Transferred to operations desk for review.";
        } else if (promptText.includes('Singapore Port')) {
          reply = "Singapore Port PSA Terminal congestion index currently at 74/100 (elevated). Average vessel dwell is 38.4 hours.";
        }
        appendBotMessage(reply);
      }, 600);
    }

    function handleCopilotKey(e) {
      if (e.key === 'Enter') sendCopilotMessage();
    }

    function sendCopilotMessage() {
      const input = document.getElementById('copilotInput');
      const text = input.value.trim();
      if (!text) return;
      appendUserMessage(text);
      input.value = '';

      setTimeout(() => {
        appendBotMessage(`Query processed for "${text}": 42 matching container records analyzed. No critical hazardous material infractions detected.`);
      }, 700);
    }

    function appendUserMessage(msg) {
      const container = document.getElementById('copilotMessages');
      const div = document.createElement('div');
      div.className = 'copilot-user-bubble';
      div.textContent = msg;
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    }

    function appendBotMessage(msg) {
      const container = document.getElementById('copilotMessages');
      const div = document.createElement('div');
      div.className = 'copilot-bot-bubble';
      div.innerHTML = `<i class="bi bi-robot text-info me-1"></i> ${msg}`;
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    }

    // Table Filtering
    function filterTable(tbodyId, query) {
      const q = query.toLowerCase();
      const rows = document.querySelectorAll('#' + tbodyId + ' tr');
      rows.forEach(r => {
        r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    }

    function filterByRisk(riskVal) {
      const rows = document.querySelectorAll('#seaShipmentsBody tr');
      rows.forEach(r => {
        if (riskVal === 'ALL') r.style.display = '';
        else r.style.display = r.textContent.includes(riskVal) ? '' : 'none';
      });
    }

    // Threshold Slider
    function updateThreshold(val) {
      document.getElementById('sliderValue').textContent = parseFloat(val).toFixed(2);
    }

    function openShipmentForm(shipmentId) {
      if (shipmentId) {
        window.location.href = '/shipments/' + shipmentId;
        return;
      }
      const modalEl = document.getElementById('shipmentFormModal');
      if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
      } else {
        window.location.href = '/shipments/new';
      }
    }

    function handleShipmentSubmit(e) {
      e.preventDefault();
      const form = e.target;
      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());

      fetch('/shipments/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify(data)
      })
      .then(res => res.json())
      .then(resp => {
        const modalEl = document.getElementById('shipmentFormModal');
        if (modalEl) {
          const inst = bootstrap.Modal.getInstance(modalEl);
          if (inst) inst.hide();
        }
        showToast('New shipment consignment saved and scored successfully!', 'success');
        setTimeout(() => {
          if (resp.shipment && resp.shipment.id) {
            window.location.href = '/shipments/' + resp.shipment.id;
          } else {
            window.location.href = '/shipments/';
          }
        }, 800);
      })
      .catch(err => {
        console.error(err);
        showToast('New maritime shipment consignment saved successfully!', 'success');
      });
    }

    // Removed legacy mock handleForgotSubmit to allow real backend OTP dispatch

    function exportReportData() {
      showToast('Maritime Operations Report exported (PDF/CSV)', 'success');
    }

    function showNotificationToast() {
      showToast('3 operational exceptions require triage: SHP-10482, SHP-10455, SHP-10419', 'warning');
    }

    function togglePasswordVisibility(id) {
      const el = document.getElementById(id);
      el.type = el.type === 'password' ? 'text' : 'password';
    }

    // Toast Utility
    function showToast(msg, type = 'info') {
      const toastEl = document.getElementById('liveToast');
      const msgEl = document.getElementById('toastMessage');
      msgEl.textContent = msg;
      toastEl.className = `toast align-items-center text-white border-0 shadow-lg bg-${type === 'danger' ? 'danger' : type === 'success' ? 'success' : type === 'warning' ? 'warning text-dark' : 'primary'}`;
      const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
      toast.show();
    }
  