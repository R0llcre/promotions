// UI-related functions for rendering promotions
import { $id, escapeHtml, formatRelativeDateRange } from "./utils.js";

let typeChartInstance = null;

export function updatePromotionsCount(count) {
  const el = $id("promotionsCount");
  if (!el) return;
  el.textContent = count + " promotion" + (count !== 1 ? "s" : "");
}

export function updateDashboardStats(items) {
  const now = new Date();
  let activeCount = 0;
  let expiringCount = 0;
  const types = { PERCENT: 0, DISCOUNT: 0, BOGO: 0 };

  items.forEach(function (p) {
    const start = new Date(p.start_date);
    const end = new Date(p.end_date);
    const isActive = start <= now && end >= now;
    if (isActive) activeCount++;

    const diffTime = Math.abs(end - now);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    if (isActive && diffDays <= 7) expiringCount++;

    types[p.promotion_type] = (types[p.promotion_type] || 0) + 1;
  });

  if ($id("statActiveCount")) $id("statActiveCount").textContent = activeCount;
  if ($id("statExpiringCount")) $id("statExpiringCount").textContent = expiringCount;
  updateTypeChart(types);
}

function updateTypeChart(typesData) {
  const ctx = document.getElementById("typeChart");
  if (!ctx || typeof Chart === "undefined") return;
  if (typeChartInstance) {
    typeChartInstance.destroy();
  }
  typeChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: Object.keys(typesData),
      datasets: [
        {
          data: Object.values(typesData),
          backgroundColor: ["#5e72e4", "#2dce89", "#11cdef"],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
      cutout: "70%",
    },
  });
}

export function renderCards(items) {
  const cardView = $id("promotions_cards_view");
  if (!cardView) return;
  cardView.innerHTML = "";

  if (!items || items.length === 0) {
    cardView.innerHTML = '<div class="empty-card-view"><p class="text-muted">No promotions to display.</p></div>';
    return;
  }

  const frag = document.createDocumentFragment();
  items.forEach(function (p) {
    const card = document.createElement("div");
    card.className = "promo-card";

    const id = escapeHtml(p.id ?? "");
    const name = escapeHtml(p.name ?? "");
    const type = escapeHtml(p.promotion_type ?? "");
    const productId = escapeHtml(p.product_id ?? "");

    const today = new Date();
    const isActive = new Date(p.start_date) <= today && new Date(p.end_date) >= today;
    const statusBadge = isActive
      ? '<span class="badge badge-soft-success">Active</span>'
      : '<span class="badge badge-soft-danger">Inactive</span>';

    let typeBadgeClass = "badge-soft-primary";
    if (p.promotion_type === "BOGO") typeBadgeClass = "badge-soft-success";
    if (p.promotion_type === "DISCOUNT") typeBadgeClass = "badge-soft-danger";
    const typeHtml = '<span class="badge ' + typeBadgeClass + '">' + type + "</span>";

    // Use database img_url if available, otherwise fall back to picsum placeholder
    const imageUrl = p.img_url || "https://picsum.photos/seed/" + (p.product_id || p.id) + "/400/260";

    card.innerHTML = [
      '<div class="promo-card-img-container">',
      '<img src="' + imageUrl + '" class="promo-card-img" alt="Promotion Image for ' + name + '">',
      "</div>",
      '<div class="promo-card-content">',
      '<div class="promo-card-actions">',
      '<button class="edit-btn" data-id="' +
        id +
        '" data-name="' +
        name +
        '" data-promotion=\'' +
        escapeHtml(JSON.stringify(p)) +
        '\'>',
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"/></svg></button>',
      '<button class="deactivate-btn" data-id="' +
        id +
        '" data-name="' +
        name +
        '">',
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-ban" viewBox="0 0 16 16"><path d="M15 8a6.973 6.973 0 0 0-1.71-4.584l-9.874 9.875A7 7 0 0 0 15 8M2.71 12.584l9.874-9.875a7 7 0 0 0-9.874 9.874ZM16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0"/></svg></button>',
      '<button class="delete-btn" data-id="' +
        id +
        '" data-name="' +
        name +
        '">',
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/><path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/></svg></button>',
      "</div>",
      '<h3 class="promo-card-title" title="' + name + '">' + name + "</h3>",
      '<div class="promo-card-tags">' + statusBadge + typeHtml + "</div>",
      '<div class="promo-card-date"> Product ID: <span class="product-id-tag">' + productId + "</span></div>",
      '<div class="promo-card-date" style="margin-top: 0.25rem;">' +
        formatRelativeDateRange(p.start_date, p.end_date) +
        "</div>",
      "</div>",
    ].join("");
    frag.appendChild(card);
  });
  cardView.appendChild(frag);
}

export function renderTable(items) {
  const tbody = document.querySelector("#promotions_table tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!items || items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No promotions available</td></tr>';
    return;
  }
  const frag = document.createDocumentFragment();
  items.forEach(function (p) {
    const tr = document.createElement("tr");
    const id = escapeHtml(p.id ?? "");
    const name = escapeHtml(p.name ?? "");
    const type = escapeHtml(p.promotion_type ?? "");
    const value = escapeHtml(p.value ?? "");
    const productId = escapeHtml(p.product_id ?? "");

    const today = new Date();
    const isActive = new Date(p.start_date) <= today && new Date(p.end_date) >= today;
    const statusBadge = isActive
      ? '<span class="badge badge-soft-success">Active</span>'
      : '<span class="badge badge-soft-danger">Inactive</span>';

    let typeBadgeClass = "badge-soft-primary";
    if (p.promotion_type === "BOGO") typeBadgeClass = "badge-soft-success";
    if (p.promotion_type === "DISCOUNT") typeBadgeClass = "badge-soft-danger";
    const typeHtml = '<span class="badge ' + typeBadgeClass + '">' + type + "</span>";

    tr.innerHTML = [
      '<td class="text-center"><span class="text-muted">#' + id + "</span></td>",
      '<td class="fw-bold">' + name + "</td>",
      "<td>" + typeHtml + "</td>",
      '<td class="text-center font-monospace">' + value + "</td>",
      '<td class="text-center"><span class="product-id-tag">' + productId + "</span></td>",
      '<td class="text-center">' + statusBadge + "</td>",
      '<td class="text-center">' + formatRelativeDateRange(p.start_date, p.end_date) + "</td>",
      '<td class="text-center" style="white-space: nowrap;">' +
        '<button class="edit-btn" data-id="' +
        id +
        '" data-name="' +
        name +
        '" data-promotion=\'' +
        escapeHtml(JSON.stringify(p)) +
        '\'>',
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"/></svg></button>',
      '<button class="deactivate-btn" data-id="' +
        id +
        '" data-name="' +
        name +
        '">',
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-ban" viewBox="0 0 16 16"><path d="M15 8a6.973 6.973 0 0 0-1.71-4.584l-9.874 9.875A7 7 0 0 0 15 8M2.71 12.584l9.874-9.875a7 7 0 0 0-9.874 9.874ZM16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0"/></svg></button>',
      '<button class="delete-btn" data-id="' +
        id +
        '" data-name="' +
        name +
        '">',
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/><path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/></svg></button>',
      "</td>",
    ].join("");
    frag.appendChild(tr);
  });
  tbody.appendChild(frag);
}
