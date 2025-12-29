// ---------------------------------------------------------
//  MAIN.JS — Global JavaScript for BYGONE Application
// ---------------------------------------------------------
//
// Sections:
//   1. Utility helpers
//   2. Accordions (location pages + route pages)
//   3. Image carousel (gallery pages)
//   4. Fullscreen lightbox viewer
//   5. Touch swipe support
//
// All code checks if elements exist before running,
// so this file is safe to load on EVERY page.
// ---------------------------------------------------------



// ---------------------------------------------------------
// 1. UTILITY HELPERS
// ---------------------------------------------------------

function exists(selector) {
    return document.querySelector(selector) !== null;
}



// ---------------------------------------------------------
// 2. ACCORDION LOGIC
// ---------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("history-accordion");
  if (!root) return;

  root.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-accordion-btn]");
    if (!btn) return;

    const panelId = btn.getAttribute("aria-controls");
    const panel = document.getElementById(panelId);
    if (!panel) return;

    const isOpen = btn.getAttribute("aria-expanded") === "true";

    // close all (single-open accordion)
    root.querySelectorAll("[data-accordion-btn]").forEach(b => b.setAttribute("aria-expanded", "false"));
    root.querySelectorAll("[data-accordion-panel]").forEach(p => p.hidden = true);

    // open selected if it wasn't already open
    if (!isOpen) {
      btn.setAttribute("aria-expanded", "true");
      panel.hidden = false;
    }
  });
});

/**
 * If the URL exists in window.images, open the lightbox at that index.
 * Otherwise, open the image in a new tab as a fallback.
 */
function openLightboxAtUrl(url) {
  const list = window.images || [];
  const idx = list.findIndex(i => i.file === url);

  if (idx >= 0) {
    window.currentIndex = idx;
    if (typeof openLightbox === "function") openLightbox();
    return;
  }

  // fallback
  window.open(url, "_blank");
}


// ---------------------------------------------------------
// 3. IMAGE CAROUSEL (Gallery Page)
// ---------------------------------------------------------

// Ensure globals exist (prevents ReferenceError on pages where template didn't set them yet)
window.images = window.images || [];
window.currentIndex = window.currentIndex || 0;

function renderCarousel() {
  const imgEl = document.getElementById("carousel-image");
  if (!images || images.length === 0) return;

  imgEl.src = images[currentIndex].file;
  imgEl.alt = images[currentIndex].title || "";

  updateCaption();
}

function updateCarousel() {
  const imgEl = document.getElementById("carousel-image");
  if (!imgEl || !window.images || window.images.length === 0) return;

  imgEl.src = images[currentIndex].file;
  imgEl.alt = images[currentIndex].title || "";

  const modalImg = document.getElementById("lightbox-img");
  if (modalImg) modalImg.src = images[currentIndex].file;
}

function nextImage() {
    if (images.length === 0) return;
    currentIndex = (currentIndex + 1) % images.length;
    updateCarousel();
    updateCaption();
}

function prevImage() {
    if (images.length === 0) return;
    currentIndex = (currentIndex - 1 + images.length) % images.length;
    updateCarousel();
    updateCaption();
}

// Initialize carousel only if it exists
document.addEventListener("DOMContentLoaded", () => {
    if (exists("#carousel-image")) {
        updateCarousel();
        updateCaption();
    }
});

// Caption Gallery Logic

function updateCaption() {
  const caption = document.getElementById("carousel-caption");
  const dateEl = document.getElementById("caption-date");
  const titleEl = document.getElementById("caption-title");
  const descEl = document.getElementById("caption-desc");
  const infoBtn = document.getElementById("caption-info-btn");

  if (!window.images || images.length === 0) return;

  const img = images[currentIndex] || {};

  dateEl.textContent = img.date || "";
  titleEl.textContent = img.title || "";
  descEl.textContent = img.description || "";

  caption.classList.add("collapsed");
  caption.classList.remove("expanded");

  const hasDesc = (img.description || "").trim().length > 0;
  infoBtn.style.display = hasDesc ? "inline-block" : "none";
}

function toggleCaption(e) {
  if (e) e.stopPropagation();

  const caption = document.getElementById("carousel-caption");
  if (!caption) return;

  const isCollapsed = caption.classList.contains("collapsed");

  caption.classList.toggle("collapsed", !isCollapsed);
  caption.classList.toggle("expanded", isCollapsed);
}

function updateLightboxCaption() {
  const caption = document.getElementById("lightbox-caption");
  const dateEl = document.getElementById("lightbox-caption-date");
  const titleEl = document.getElementById("lightbox-caption-title");
  const descEl = document.getElementById("lightbox-caption-desc");
  const infoBtn = document.getElementById("lightbox-caption-info-btn");

  if (!caption || !dateEl || !titleEl || !descEl || !infoBtn) return;
  if (!window.images || images.length === 0) return;

  const img = images[currentIndex] || {};
  dateEl.textContent = img.date || "";
  titleEl.textContent = img.title || "";
  descEl.textContent = img.description || "";

  caption.classList.add("collapsed");
  caption.classList.remove("expanded");

  const hasDesc = (img.description || "").trim().length > 0;
  infoBtn.style.display = hasDesc ? "inline-block" : "none";
  infoBtn.textContent = "ⓘ";
}

function toggleLightboxCaption(e) {
  if (e) e.stopPropagation();

  const caption = document.getElementById("lightbox-caption");
  const infoBtn = document.getElementById("lightbox-caption-info-btn");
  if (!caption || !infoBtn) return;

  const willExpand = caption.classList.contains("collapsed");
  caption.classList.toggle("collapsed", !willExpand);
  caption.classList.toggle("expanded", willExpand);

  infoBtn.textContent = willExpand ? "✕" : "ⓘ";
}

//end caption logic

// ---------------------------------------------------------
// 4. FULLSCREEN LIGHTBOX VIEWER
// ---------------------------------------------------------

function openLightbox(index = currentIndex) {
  currentIndex = index;

  const lb = document.getElementById("lightbox");
  const lbImg = document.getElementById("lightbox-img");

  lb.style.display = "flex"; // or add a class if you prefer
  lbImg.src = images[currentIndex].file;
  lbImg.alt = images[currentIndex].title || "";

  // optional: prevent background scroll on mobile
  document.body.style.overflow = "hidden";

  updateLightboxCaption();
}

function closeLightbox(e) {
  // allow calls from button clicks; stop bubbling so overlay click doesn't fire twice
  if (e) e.stopPropagation();

  const lb = document.getElementById("lightbox");
  lb.style.display = "none";

  document.body.style.overflow = "";
}

function setLightboxImage() {
  const lbImg = document.getElementById("lightbox-img");
  lbImg.src = images[currentIndex].file;
  lbImg.alt = images[currentIndex].title || "";

  // keep carousel in sync (so when they close, the main image matches)
  renderCarousel();

  updateLightboxCaption();
}

function lightboxPrev(e) {
  e.stopPropagation();
  if (!images || images.length === 0) return;

  currentIndex = (currentIndex - 1 + images.length) % images.length;
  setLightboxImage();
}

function lightboxNext(e) {
  e.stopPropagation();
  if (!images || images.length === 0) return;

  currentIndex = (currentIndex + 1) % images.length;
  setLightboxImage();
}


// ---------------------------------------------------------
// 5. SWIPE GESTURES (Gallery Page)
// ---------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    const img = document.getElementById("carousel-image");
    if (!img) return;

    let startX = 0;

    img.addEventListener("touchstart", (e) => {
        startX = e.touches[0].clientX;
    });

    img.addEventListener("touchend", (e) => {
        const endX = e.changedTouches[0].clientX;
        const diff = startX - endX;

        if (Math.abs(diff) > 50) {
            if (diff > 0) nextImage();   // swipe left
            else prevImage();            // swipe right
        }
    });
});

// ---------------------------------------------------------
// END OF main.js
// ---------------------------------------------------------
