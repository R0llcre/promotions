import {
  fetchPromotions,
  createPromotion,
  updatePromotion,
  deletePromotion,
  deactivatePromotion,
} from "./api.js";
import {
  renderCards,
  renderTable,
  updateDashboardStats,
  updatePromotionsCount,
} from "./ui.js";
import {
  $id,
  formatDateShort,
  normalizeDateInput,
  normalizeResponse,
  showSuccessToast,
} from "./utils.js";

let allPromotions = [];
let currentView = "table"; // 'table' or 'card'
const currentFilters = {
  active: null,
  name: null,
  type: null,
  productId: null,
};

function render() {
  updateDashboardStats(allPromotions);
  updatePromotionsCount(allPromotions.length);
  if (currentView === "table") {
    renderTable(allPromotions);
  } else {
    renderCards(allPromotions);
  }
}

function showLoading(view) {
  const tableView = $id("promotions_table_view");
  const cardView = $id("promotions_cards_view");
  if (view === "table" && tableView?.querySelector("tbody")) {
    tableView.querySelector("tbody").innerHTML =
      '<tr><td colspan="8" class="text-center small text-muted">Loading...</td></tr>';
  } else if (view === "card" && cardView) {
    cardView.innerHTML = '<div class="text-center small text-muted p-5">Loading...</div>';
  }
}

async function loadAndRender(queryParams) {
  showLoading(currentView);
  try {
    const json = await fetchPromotions(queryParams);
    allPromotions = normalizeResponse(json);
  } catch (err) {
    console.error(err);
    allPromotions = [];
  }
  render();
}

function initViewSwitcher() {
  const viewTableBtn = $id("view-table-btn");
  const viewCardBtn = $id("view-card-btn");
  const tableView = $id("promotions_table_view");
  const cardView = $id("promotions_cards_view");

  function switchView(view) {
    if (currentView === view) return;
    currentView = view;

    if (view === "table") {
      tableView.classList.remove("d-none");
      cardView.classList.add("d-none");
      viewTableBtn.classList.add("active");
      viewCardBtn.classList.remove("active");
    } else {
      tableView.classList.add("d-none");
      cardView.classList.remove("d-none");
      viewTableBtn.classList.remove("active");
      viewCardBtn.classList.add("active");
    }
    render();
  }

  if (viewTableBtn) viewTableBtn.addEventListener("click", function () { switchView("table"); });
  if (viewCardBtn) viewCardBtn.addEventListener("click", function () { switchView("card"); });
}

function initCreateModal() {
  const createModalEl = $id("createModal");
  const createModal = bootstrap.Modal.getOrCreateInstance(createModalEl);

  createModalEl?.addEventListener("shown.bs.modal", function () { $id("inputName")?.focus(); });
  createModalEl?.addEventListener("hidden.bs.modal", function () {
    $id("createForm")?.reset();
    $id("createForm")?.classList.remove("was-validated");
    $id("createError")?.classList.add("d-none");
  });

  $id("createForm")?.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    this.classList.add("was-validated");
    if (!this.checkValidity()) return;

    const imgUrlValue = ($id("inputImgUrl").value || "").trim();
    const payload = {
      name: ($id("inputName").value || "").trim(),
      promotion_type: ($id("inputType").value || "").trim(),
      value: Number($id("inputValue").value),
      product_id: parseInt($id("inputProductId").value, 10) || null,
      img_url: imgUrlValue || null,
      start_date: normalizeDateInput($id("inputStart").value),
      end_date: normalizeDateInput($id("inputEnd").value),
    };

    const submitBtn = $id("createSubmit");
    if (submitBtn) submitBtn.disabled = true;

    try {
      await createPromotion(payload);
      createModal.hide();
      showSuccessToast("Promotion created");
      loadAndRender();
    } catch (err) {
      console.error("Create failed:", err);
      const ce = $id("createError");
      if (ce) {
        ce.classList.remove("d-none");
        ce.textContent = err.message;
      }
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

function initDeleteModal() {
  const deleteModalEl = $id("deleteModal");
  const deleteModal = bootstrap.Modal.getOrCreateInstance(deleteModalEl);
  let currentDeleteId = null;

  document.addEventListener("click", function (e) {
    const deleteBtn = e.target.closest(".delete-btn");
    if (deleteBtn) {
      currentDeleteId = deleteBtn.dataset.id;
      $id("deletePromotionId").textContent = currentDeleteId;
      $id("deletePromotionName").textContent = deleteBtn.dataset.name;
      deleteModal.show();
    }
  });

  $id("confirmDelete")?.addEventListener("click", async function () {
    if (!currentDeleteId) return;
    this.disabled = true;
    try {
      await deletePromotion(currentDeleteId);
      deleteModal.hide();
      showSuccessToast("Promotion deleted");
      loadAndRender();
    } catch (err) {
      console.error("Delete failed:", err);
      alert("Failed to delete promotion: " + err.message);
    } finally {
      this.disabled = false;
      currentDeleteId = null;
    }
  });
}

function initDeactivateModal() {
  const deactivateModalEl = $id("deactivateModal");
  const deactivateModal = bootstrap.Modal.getOrCreateInstance(deactivateModalEl);
  let currentDeactivateId = null;

  document.addEventListener("click", function (e) {
    const deactivateBtn = e.target.closest(".deactivate-btn");
    if (deactivateBtn) {
      currentDeactivateId = deactivateBtn.dataset.id;
      $id("deactivatePromotionId").textContent = currentDeactivateId;
      $id("deactivatePromotionName").textContent = deactivateBtn.dataset.name;
      deactivateModal.show();
    }
  });

  $id("confirmDeactivate")?.addEventListener("click", async function () {
    if (!currentDeactivateId) return;
    this.disabled = true;
    try {
      await deactivatePromotion(currentDeactivateId);
      deactivateModal.hide();
      showSuccessToast("Promotion deactivated");
      loadAndRender();
    } catch (err) {
      console.error("Deactivate failed:", err);
      alert("Failed to deactivate promotion: " + err.message);
    } finally {
      this.disabled = false;
      currentDeactivateId = null;
    }
  });
}

function initEditModal() {
  const editModalEl = $id("editModal");
  const editModal = bootstrap.Modal.getOrCreateInstance(editModalEl);
  let currentEditId = null;

  document.addEventListener("click", function (e) {
    const editBtn = e.target.closest(".edit-btn");
    if (editBtn) {
      try {
        const promotion = JSON.parse(editBtn.dataset.promotion);
        currentEditId = promotion.id;
        $id("editId").value = promotion.id;
        $id("editName").value = promotion.name || "";
        $id("editType").value = promotion.promotion_type || "";
        $id("editValue").value = promotion.value ?? "";
        $id("editProductId").value = promotion.product_id ?? "";
        $id("editImgUrl").value = promotion.img_url || "";
        $id("editStart").value = formatDateShort(promotion.start_date) || "";
        $id("editEnd").value = formatDateShort(promotion.end_date) || "";
        editModal.show();
      } catch (err) {
        console.error("Failed to parse promotion data for edit:", err);
      }
    }
  });

  $id("editForm")?.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    this.classList.add("was-validated");
    if (!this.checkValidity() || !currentEditId) return;

    const imgUrlValue = ($id("editImgUrl").value || "").trim();
    const payload = {
      name: ($id("editName").value || "").trim(),
      promotion_type: ($id("editType").value || "").trim(),
      value: Number($id("editValue").value),
      product_id: parseInt($id("editProductId").value, 10) || null,
      img_url: imgUrlValue || null,
      start_date: normalizeDateInput($id("editStart").value),
      end_date: normalizeDateInput($id("editEnd").value),
    };

    const submitBtn = $id("editSubmit");
    if (submitBtn) submitBtn.disabled = true;

    try {
      await updatePromotion(currentEditId, payload);
      editModal.hide();
      showSuccessToast("Promotion updated");
      loadAndRender();
    } catch (err) {
      console.error("Update failed:", err.message);
      const ee = $id("editError");
      if (ee) {
        ee.classList.remove("d-none");
        ee.textContent = err.message;
      }
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });

  editModalEl?.addEventListener("hidden.bs.modal", function () {
    $id("editForm")?.classList.remove("was-validated");
    $id("editError")?.classList.add("d-none");
    currentEditId = null;
  });
}

function initFilters() {
  const searchInput = $id("searchInput");
  const filterPills = document.querySelectorAll(".filter-pill");
  const filterType = $id("filterType");
  const filterProductId = $id("filterProductId");
  const btnClearFilters = $id("btnClearFilters");
  let searchTimeout = null;

  function applyFilters() {
    const queryParams = new URLSearchParams();
    if (currentFilters.active && currentFilters.active !== "all") {
      queryParams.set("active", currentFilters.active === "active");
    }
    if (currentFilters.name) {
      queryParams.set("name", currentFilters.name);
    }
    if (currentFilters.type) {
      queryParams.set("promotion_type", currentFilters.type);
    }
    if (currentFilters.productId) {
      queryParams.set("product_id", currentFilters.productId);
    }

    const qs = queryParams.toString();
    const newUrl = qs ? window.location.pathname + "?" + qs : window.location.pathname;
    window.history.pushState({}, "", newUrl);
    loadAndRender(qs);
  }

  function resetOtherFilters(except) {
    if (except !== "name") {
      currentFilters.name = null;
      if (searchInput) searchInput.value = "";
    }
    if (except !== "active") {
      currentFilters.active = null;
      filterPills.forEach((p) => p.classList.remove("active"));
    }
    if (except !== "type") {
      currentFilters.type = null;
      if (filterType) filterType.value = "";
    }
    if (except !== "productId") {
      currentFilters.productId = null;
      if (filterProductId) filterProductId.value = "";
    }
  }

  searchInput?.addEventListener("input", function (e) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(function () {
      resetOtherFilters("name");
      currentFilters.name = e.target.value.trim();
      applyFilters();
    }, 300);
  });

  filterPills.forEach(function (pill) {
    pill.addEventListener("click", function () {
      resetOtherFilters("active");
      filterPills.forEach(function (p) { p.classList.remove("active"); });
      this.classList.add("active");
      currentFilters.active = this.dataset.filter;
      applyFilters();
    });
  });

  filterType?.addEventListener("change", function (e) {
    resetOtherFilters("type");
    currentFilters.type = e.target.value;
    applyFilters();
  });

  filterProductId?.addEventListener("input", function (e) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(function () {
      resetOtherFilters("productId");
      currentFilters.productId = e.target.value.trim();
      applyFilters();
    }, 300);
  });

  btnClearFilters?.addEventListener("click", function () {
    resetOtherFilters("none");
    const allPill = document.querySelector('.filter-pill[data-filter="all"]');
    if (allPill) allPill.classList.add("active");
    applyFilters();
  });
}

document.addEventListener("DOMContentLoaded", function () {
  loadAndRender();
  initViewSwitcher();
  initCreateModal();
  initDeleteModal();
  initDeactivateModal();
  initEditModal();
  initFilters();
});
