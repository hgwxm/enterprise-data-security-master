/* ══════════════════════════════════════════════════════════════
   AegisData · 企业数据安全管理平台
   第一阶段前端初稿 · 共享数据层 + 页面控制器
   ──────────────────────────────────────────────────────────────
   ⚠️ 本文件只负责「呈现」，不实现任何权限判断规则。
      DEMO_DECISIONS 是纯前端预置的演示数据，用于固定信息层级；
      接入后端统一入口 check_permission(user_role, file_id, action)
      之后，必须整体删除 DEMO_DECISIONS 与 resolve()，改为请求
      POST /api/access 获取 { request_id, decision, reason, executed }。

   页面通过 <body data-page="..."> 声明身份：
     console → 访问控制台      audit → 审计日志
     rules   → 权限规则（只读） about → 系统说明（只读）
   ══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ══════════ 1. 字典：只能来自 docs/file_list.md 与 docs/permission_rules.md ══════════ */

  const ROLES = {
    employee: '普通员工 · employee',
    finance:  '财务人员 · finance',
    admin:    '管理员 · admin'
  };

  /* 表格等窄栏位使用的角色简称 */
  const ROLE_SHORT = {
    employee: '普通员工',
    finance:  '财务人员',
    admin:    '管理员'
  };

  const FILES = {
    F001: 'F001 · 普通业务报告',
    F002: 'F002 · 内部财务报告',
    F003: 'F003 · 敏感工资表'
  };

  const ACTIONS = {
    read:   '读取',
    export: '导出'
  };

  /* ══════════ 2. 后端接口调用 ══════════
     接入后端统一入口 POST /api/access，
     获取 { request_id, decision, reason, executed, timestamp }。
     DEMO_DECISIONS 与 resolve() 已删除。 ══════════ */

  async function fetchAccess(role, fileId, action) {
    try {
      var resp = await fetch('/api/access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_role: role, file_id: fileId, action: action })
      });
      if (!resp.ok) {
        return { decision: 'DENY', reason: '后端请求失败（HTTP ' + resp.status + '）', request_id: '', executed: false, timestamp: '' };
      }
      var data = await resp.json();
      return {
        decision:   data.decision || 'DENY',
        reason:     data.reason || '未知原因',
        request_id: data.request_id || '',
        executed:   !!data.executed,
        timestamp:  data.timestamp || ''
      };
    } catch (e) {
      return { decision: 'DENY', reason: '无法连接后端服务', request_id: '', executed: false, timestamp: '' };
    }
  }

  /* 判定结果的呈现文案与图标 */
  const ICONS = {
    ALLOW:            '<path d="M5 12.6l4.4 4.4L19 7.4" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
    DENY:             '<circle cx="12" cy="12" r="8.2" stroke="currentColor" stroke-width="2"/><path d="M6.4 17.6 17.6 6.4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    PENDING_APPROVAL: '<circle cx="12" cy="12" r="8.2" stroke="currentColor" stroke-width="2"/><path d="M12 7.4V12l3.2 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
  };

  const VERDICT = {
    ALLOW: {
      cls:        'is-allow',
      title:      '操作允许',
      sub:        '权限检查通过，文件操作已在受控流程中执行',
      proofTitle: '文件操作已执行',
      proofDesc:  '判定为 ALLOW，操作已在受控流程中完成，实际结果已写入审计日志。',
      executed:   true
    },
    DENY: {
      cls:        'is-deny',
      title:      '操作拒绝',
      sub:        '权限规则不允许该操作，已在文件操作之前拦截',
      proofTitle: '已证明：文件操作没有执行',
      proofDesc:  '判定为 DENY，系统在真实文件操作之前完成拦截，未读取、未导出目标文件。',
      executed:   false
    },
    PENDING_APPROVAL: {
      cls:        'is-pending',
      title:      '待审批',
      sub:        '该操作需要人工审批，审批完成前不得执行',
      proofTitle: '已证明：审批完成前没有执行',
      proofDesc:  '判定为 PENDING_APPROVAL，操作进入审批流程，审批通过前未读取、未导出目标文件。',
      executed:   false
    }
  };

  /* ══════════ 3. 权限判定已移至后端 POST /api/access ══════════ */

  /* ══════════ 4. 存储：记录跨页面共享（演示用 localStorage） ══════════ */

  const STORE_KEY = 'aegisdata.records.v1';

  const store = (function () {
    let memory = [];
    let usable = false;
    try {
      window.localStorage.setItem('__t', '1');
      window.localStorage.removeItem('__t');
      usable = true;
    } catch (e) {
      usable = false;   /* file:// 下某些浏览器禁用 localStorage，退回内存存储 */
    }
    return {
      all: function () {
        if (!usable) return memory;
        try {
          const raw = window.localStorage.getItem(STORE_KEY);
          return raw ? JSON.parse(raw) : [];
        } catch (e) { return []; }
      },
      save: function (list) {
        if (!usable) { memory = list; return; }
        try {
          window.localStorage.setItem(STORE_KEY, JSON.stringify(list));
        } catch (e) { memory = list; }
      },
      clear: function () {
        memory = [];
        if (!usable) return;
        try { window.localStorage.removeItem(STORE_KEY); } catch (e) { /* 忽略 */ }
      },
      persistent: usable
    };
  })();

  /* ══════════ 5. 工具 ══════════ */

  const $ = function (id) { return document.getElementById(id); };

  function pad(n) { return String(n).padStart(2, '0'); }

  function stamp(d) {
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
           ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }

  function makeRequestId(d, n) {
    return 'REQ' + d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) +
           pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds()) +
           String(n).padStart(2, '0');
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  const ICON_EXEC_YES = '<svg viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7.2" stroke="currentColor" stroke-width="1.6"/><path d="M6.8 10.2l2.3 2.3 4.1-4.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const ICON_EXEC_NO  = '<svg viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7.2" stroke="currentColor" stroke-width="1.6"/><path d="M7.2 10h5.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';

  /* 表格里的判定徽标：PENDING_APPROVAL 太长，窄栏位显示为"待审批" */
  function decisionTag(decision) {
    const map = {
      ALLOW:            ['tag--allow',   'ALLOW'],
      DENY:             ['tag--deny',    'DENY'],
      PENDING_APPROVAL: ['tag--pending', '待审批']
    };
    const item = map[decision] || ['tag--deny', decision];
    return '<span class="tag ' + item[0] + '" title="' + esc(decision) + '">' + item[1] + '</span>';
  }

  function execCell(decision) {
    const v = VERDICT[decision] || VERDICT.DENY;
    return v.executed
      ? '<span class="exec exec--yes">' + ICON_EXEC_YES + '已执行</span>'
      : '<span class="exec exec--no">'  + ICON_EXEC_NO  + '未执行</span>';
  }

  /* 历史表格行（控制台与审计页共用） */
  function historyRow(r) {
    return '<tr' + (r.isNew ? ' class="is-new"' : '') + '>' +
      '<td class="mono c-time">' + esc(r.time) + '</td>' +
      '<td class="mono c-req" title="' + esc(r.requestId) + '">' + esc(r.requestId) + '</td>' +
      '<td title="' + esc(ROLES[r.role] || r.role) + '">' + esc(ROLE_SHORT[r.role] || r.role) + '</td>' +
      '<td><span class="tag-code">' + esc(r.fileId) + '</span></td>' +
      '<td class="c-act">' + esc(ACTIONS[r.action] || r.action) + '</td>' +
      '<td>' + decisionTag(r.decision) + '</td>' +
      '<td class="reason" title="' + esc(r.reason) + '">' + esc(r.reason) + '</td>' +
      '<td class="ta-c">' + execCell(r.decision) + '</td>' +
    '</tr>';
  }

  function emptyRow(text) {
    return '<tr><td colspan="8" class="empty">' + text + '</td></tr>';
  }

  function updateNavCount() {
    const n = $('navCount');
    if (n) n.textContent = String(store.all().length);
  }

  /* ══════════ 6. 控制台页 ══════════ */

  function initConsole() {
    let seq = 0;

    const el = {
      form:        $('requestForm'),
      role:        $('role'),
      file:        $('file'),
      action:      $('action'),
      submitBtn:   $('submitBtn'),
      result:      $('result'),
      badge:       $('decisionBadge'),
      verdictIcon: document.querySelector('.verdict__icon svg'),
      vTitle:      $('verdictTitle'),
      vSub:        $('verdictSub'),
      kvRequestId: $('kvRequestId'),
      kvDecision:  $('kvDecision'),
      kvRole:      $('kvRole'),
      kvReason:    $('kvReason'),
      kvFile:      $('kvFile'),
      kvExecuted:  $('kvExecuted'),
      kvAction:    $('kvAction'),
      kvTime:      $('kvTime'),
      proofTitle:  $('proofTitle'),
      proofDesc:   $('proofDesc'),
      btnView:     $('btnView'),
      btnExport:   $('btnExport'),
      resultNote:  $('resultNote'),
      historyBody: $('historyBody'),
      search:      $('search'),
      live:        $('live')
    };

    /* 把最近一次记录渲染进结果卡片 */
    function renderResult(rec) {
      const v = VERDICT[rec.decision] || VERDICT.DENY;

      el.result.classList.remove('is-allow', 'is-deny', 'is-pending');
      el.result.classList.add(v.cls);
      el.result.dataset.decision = rec.decision;

      el.badge.textContent = rec.decision;
      el.vTitle.textContent = v.title;
      el.vSub.textContent = v.sub;
      if (el.verdictIcon) el.verdictIcon.innerHTML = ICONS[rec.decision] || ICONS.DENY;

      el.kvRequestId.textContent = rec.requestId;
      el.kvDecision.textContent = rec.decision;
      el.kvRole.textContent = ROLES[rec.role] || rec.role;
      el.kvReason.textContent = rec.reason;
      el.kvFile.textContent = FILES[rec.fileId] || rec.fileId;
      el.kvAction.textContent = ACTIONS[rec.action] || rec.action;
      el.kvTime.textContent = rec.time;
      el.kvExecuted.textContent = v.executed ? '已执行' : '未执行';
      el.kvExecuted.style.color = v.executed ? 'var(--allow)' : 'var(--ink-2)';
      el.kvExecuted.style.fontWeight = '600';

      el.proofTitle.textContent = v.proofTitle;
      el.proofDesc.textContent = v.proofDesc;

      el.btnView.disabled = !v.executed;
      el.btnExport.disabled = !(v.executed && rec.action === 'export');
      /* 读取请求没有可下载的产物，直接不显示下载按钮 */
      el.btnExport.hidden = (rec.action !== 'export');
      el.resultNote.textContent = '判定时间 ' + rec.time;

      el.result.classList.remove('is-flash');
      void el.result.offsetWidth;
      el.result.classList.add('is-flash');
    }

    function renderHistory() {
      const kw = (el.search.value || '').trim().toLowerCase();
      const all = store.all();
      const rows = all.filter(function (r) {
        if (!kw) return true;
        return (r.requestId + ' ' + r.fileId + ' ' + r.role + ' ' + r.decision)
          .toLowerCase().indexOf(kw) !== -1;
      }).slice(0, 10);

      el.historyBody.innerHTML = rows.length
        ? rows.map(historyRow).join('')
        : emptyRow(all.length ? '没有匹配的记录' : '暂无操作记录，提交一次访问申请试试');

      updateNavCount();
    }

    /* 首屏那次自动判定不算用户操作，不触发滚动 */
    let userInitiated = false;

    async function submit(role, fileId, action) {
      const now = new Date();
      const verdict = await fetchAccess(role, fileId, action);

      const rec = {
        requestId: verdict.request_id || makeRequestId(now, ++seq),
        time:      verdict.timestamp || stamp(now),
        role:      role,
        fileId:    fileId,
        action:    action,
        decision:  verdict.decision,
        reason:    verdict.reason,
        isNew:     true
      };

      renderResult(rec);

      const all = store.all();
      all.forEach(function (r) { r.isNew = false; });
      all.unshift(rec);
      while (all.length > 200) all.pop();
      store.save(all);
      renderHistory();

      if (el.live) {
        el.live.textContent = rec.requestId + ' ' + rec.decision + '：' + rec.reason;
      }

      /* 窄屏时结果区在表单下方，滚动过去；但首屏那次自动判定不滚，避免一打开就"跳" */
      if (userInitiated && window.innerWidth < 1220) {
        el.result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }

    /* ── 事件 ── */
    el.form.addEventListener('submit', function (e) {
      e.preventDefault();
      userInitiated = true;
      const btn = el.submitBtn;
      btn.disabled = true;
      submit(el.role.value, el.file.value, el.action.value).then(function () {
        btn.disabled = false;
      });
    });

    Array.prototype.forEach.call(document.querySelectorAll('.tbtn'), function (b) {
      b.addEventListener('click', function () {
        el.role.value = b.dataset.r;
        el.file.value = b.dataset.f;
        el.action.value = b.dataset.a;
        el.form.dispatchEvent(new Event('submit', { cancelable: true }));
      });
    });

    el.search.addEventListener('input', renderHistory);

    /* ── 首次进入：不再预置演示记录，后端审计库已有真实数据 ── */

    /* 初始展示一次「允许」判定，避免结果卡空白 */
    renderHistory();
    submit('employee', 'F001', 'read');
    const all = store.all();
    if (all[0]) { all[0].isNew = false; store.save(all); }
    renderHistory();

    return {
      refresh: function () {
        renderHistory();
      }
    };
  }

  /* ══════════ 7. 审计日志页 ══════════ */

  function initAudit() {
    const state = { decision: 'ALL', exec: 'ALL', kw: '' };

    const el = {
      body:        $('auditBody'),
      search:      $('search'),
      segDecision: $('segDecision'),
      segExec:     $('segExec'),
      btnClear:    $('btnClear'),
      scrim:       $('scrim'),
      drawer:      $('drawer'),
      drawerClose: $('drawerClose'),
      drawerTitle: $('drawerTitle'),
      drawerSub:   $('drawerSub'),
      drawerVerdict: $('drawerVerdict'),
      drawerFields:  $('drawerFields'),
      drawerProof:   $('drawerProof'),
      drawerProofTitle: $('drawerProofTitle'),
      drawerProofDesc:  $('drawerProofDesc'),
      statTotal:   $('statTotal'),
      statAllow:   $('statAllow'),
      statDeny:    $('statDeny'),
      statPending: $('statPending')
    };

    let openId = null;
    let started = false;
    let auditRecords = [];
    let auditLoading = false;

    /* 从后端拉取审计日志，缓存到 auditRecords */
    function fetchAuditLogs() {
      auditLoading = true;
      return fetch('/api/audit/logs?limit=200')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          auditRecords = (data.logs || []).map(function (r) {
            return {
              requestId: r.request_id,
              time:      r.timestamp,
              role:      r.user_role,
              fileId:    r.file_id,
              action:    r.action,
              decision:  r.decision,
              reason:    r.reason,
              isNew:     false
            };
          });
          auditLoading = false;
        })
        .catch(function () { auditLoading = false; });
    }

    /* 单文件版：审计页区块初始是 hidden，首次进入该页时才真正渲染 */
    function start() {
      if (started) return;
      started = true;
      fetchAuditLogs().then(render);
    }

    function filtered() {
      const kw = state.kw.toLowerCase();
      return auditRecords.filter(function (r) {
        if (state.decision !== 'ALL' && r.decision !== state.decision) return false;

        const v = VERDICT[r.decision] || VERDICT.DENY;
        if (state.exec === 'yes' && !v.executed) return false;
        if (state.exec === 'no'  &&  v.executed) return false;

        if (!kw) return true;
        return (r.requestId + ' ' + r.fileId + ' ' + r.role + ' ' + r.decision + ' ' + r.reason)
          .toLowerCase().indexOf(kw) !== -1;
      });
    }

    function renderStats() {
      const all = auditRecords;
      el.statTotal.textContent = String(all.length);
      el.statAllow.textContent = String(all.filter(function (r) { return r.decision === 'ALLOW'; }).length);
      el.statDeny.textContent  = String(all.filter(function (r) { return r.decision === 'DENY'; }).length);
      el.statPending.textContent = String(all.filter(function (r) { return r.decision === 'PENDING_APPROVAL'; }).length);
      updateNavCount();
    }

    function renderTable() {
      const rows = filtered();
      if (!rows.length) {
        el.body.innerHTML = emptyRow(auditRecords.length ? '没有符合筛选条件的记录' : '暂无日志，去访问控制台发起一次申请');
        return;
      }
      el.body.innerHTML = rows.map(function (r) {
        return historyRow(r)
          .replace(' class="is-new"', '')
          .replace('<tr', '<tr data-id="' + esc(r.requestId) + '" tabindex="0" class="is-row' +
                   (r.isNew ? ' is-new' : '') + '"');
      }).join('');

      Array.prototype.forEach.call(el.body.querySelectorAll('tr[data-id]'), function (tr) {
        tr.setAttribute('aria-selected', String(tr.dataset.id === openId));
        tr.addEventListener('click', function () { openDrawer(tr.dataset.id); });
        tr.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openDrawer(tr.dataset.id); }
        });
      });
    }

    function render() { renderStats(); renderTable(); }

    /* ── 详情抽屉 ── */
    function openDrawer(id) {
      const rec = auditRecords.filter(function (r) { return r.requestId === id; })[0];
      if (!rec) return;

      const v = VERDICT[rec.decision] || VERDICT.DENY;
      openId = id;

      el.drawerTitle.textContent = rec.requestId;
      el.drawerSub.textContent = rec.time + ' · ' + (ACTIONS[rec.action] || rec.action) +
                                 ' · ' + (FILES[rec.fileId] || rec.fileId);

      el.drawerVerdict.innerHTML =
        '<span class="badge" style="border-color:' +
        (rec.decision === 'ALLOW' ? 'var(--allow-line)' : rec.decision === 'DENY' ? 'var(--deny-line)' : 'var(--pending-line)') +
        ';color:' +
        (rec.decision === 'ALLOW' ? 'var(--allow)' : rec.decision === 'DENY' ? 'var(--deny)' : 'var(--pending)') +
        '">' + esc(rec.decision) + '</span>' +
        '<p style="margin-top:10px;font-size:13px;color:var(--ink-2)">' + esc(v.sub) + '</p>';

      const fields = [
        ['id',         rec.requestId],
        ['timestamp',  rec.time],
        ['request_id', rec.requestId],
        ['user_role',  rec.role],
        ['file_id',    rec.fileId],
        ['action',     rec.action],
        ['decision',   rec.decision],
        ['reason',     rec.reason],
        ['executed',   v.executed ? 'true' : 'false']
      ];
      el.drawerFields.innerHTML = fields.map(function (f) {
        return '<div class="dl__row"><dt>' + f[0] + '</dt><dd class="mono">' + esc(f[1]) + '</dd></div>';
      }).join('');

      el.drawerProof.classList.remove('is-allow');
      el.drawerProof.className = 'proof ' + v.cls;
      el.drawerProofTitle.textContent = v.proofTitle;
      el.drawerProofDesc.textContent = v.proofDesc;

      el.drawer.classList.add('is-open');
      el.drawer.setAttribute('aria-hidden', 'false');
      el.scrim.classList.add('is-open');
      renderTable();
    }

    function closeDrawer() {
      openId = null;
      el.drawer.classList.remove('is-open');
      el.drawer.setAttribute('aria-hidden', 'true');
      el.scrim.classList.remove('is-open');
      renderTable();
    }

    el.drawerClose.addEventListener('click', closeDrawer);
    el.scrim.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeDrawer();
    });

    /* ── 筛选事件 ── */
    el.segDecision.addEventListener('click', function (e) {
      const b = e.target.closest('.seg__btn');
      if (!b) return;
      start();
      state.decision = b.dataset.d;
      Array.prototype.forEach.call(el.segDecision.querySelectorAll('.seg__btn'), function (x) {
        x.setAttribute('aria-pressed', String(x === b));
      });
      renderTable();
    });

    el.segExec.addEventListener('click', function (e) {
      const b = e.target.closest('.seg__btn');
      if (!b) return;
      start();
      state.exec = b.dataset.e;
      Array.prototype.forEach.call(el.segExec.querySelectorAll('.seg__btn'), function (x) {
        x.setAttribute('aria-pressed', String(x === b));
      });
      renderTable();
    });

    el.search.addEventListener('input', function () {
      start();
      state.kw = el.search.value || '';
      renderTable();
    });

    el.btnClear.addEventListener('click', function () {
      start();
      if (!auditRecords.length) return;
      if (window.confirm('确定清空全部审计日志记录吗？')) {
        fetch('/api/audit/clear', { method: 'POST' })
          .then(function () { return fetchAuditLogs(); })
          .then(function () { closeDrawer(); render(); });
      }
    });

    render();

    return {
      refresh: function () {
        if (started) fetchAuditLogs().then(render);
      }
    };
  }

  /* ══════════ 8. hash 路由 ══════════
     多文件版：每个链接指向独立页面（#console → index.html）。
     单文件版：四个页面区块都在同一个文档里，由这里切换显示。
     ------------------------------------------------ */

  const ROUTES = ['console', 'audit', 'rules', 'about'];

  function currentRoute() {
    const h = (window.location.hash || '').replace(/^#/, '');
    return ROUTES.indexOf(h) !== -1 ? h : 'console';
  }

  function isSingleFile() {
    return !!(document.body.dataset.single && document.querySelector('[data-page-section]'));
  }

  function activate(route) {
    document.body.dataset.page = route;

    Array.prototype.forEach.call(document.querySelectorAll('[data-page-section]'), function (sec) {
      sec.hidden = (sec.dataset.pageSection !== route);
    });

    Array.prototype.forEach.call(document.querySelectorAll('.nav__item[data-nav]'), function (a) {
      const on = a.dataset.nav === route;
      a.classList.toggle('is-active', on);
      if (on) { a.setAttribute('aria-current', 'page'); } else { a.removeAttribute('aria-current'); }
    });

    window.scrollTo(0, 0);
  }

  function initSection(route) {
    if (route === 'console') {
      if (!window.__aegis.console) window.__aegis.console = initConsole();
      else window.__aegis.console.refresh();
    } else if (route === 'audit') {
      if (!window.__aegis.audit) window.__aegis.audit = initAudit();
      else window.__aegis.audit.refresh();
    }
  }

  /* ══════════ 9. 启动 ══════════ */

  function boot() {
    const single = isSingleFile();
    updateNavCount();

    if (!single) {
      /* 多文件版：当前文档就是当前页，直接初始化 */
      const page = document.body.dataset.page || '';
      if (page === 'console') initConsole();
      else if (page === 'audit') initAudit();
      return;
    }

    /* 单文件版：按 hash 切页 */
    if (!window.location.hash) {
      try { window.history.replaceState(null, '', '#console'); } catch (e) { /* 忽略 */ }
    }

    Array.prototype.forEach.call(document.querySelectorAll('.nav__item[data-nav]'), function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        const route = a.dataset.nav;
        if (currentRoute() === route) {
          activate(route);
        } else {
          window.location.hash = route;
        }
      });
    });

    window.addEventListener('hashchange', function () {
      const route = currentRoute();
      activate(route);
      initSection(route);
    });

    const first = currentRoute();
    activate(first);
    initSection(first);
  }

  window.__aegis = window.__aegis || {};

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
