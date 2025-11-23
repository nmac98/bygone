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
    const titles = document.querySelectorAll(".accordion-title");

    if (titles.length > 0) {
        titles.forEach(btn => {
            btn.addEventListener("click", () => {
                btn.closest(".accordion-item").classList.toggle("open");
            });
        });
    }
});



// ---------------------------------------------------------
// 3. IMAGE CAROUSEL (Gallery Page)
// ---------------------------------------------------------

function updateCarousel() {
    const imgEl = document.getElementById("carousel-image");
    if (!imgEl || images.length === 0) return;

    imgEl.src = images[currentIndex].file;
    imgEl.alt = images[currentIndex].title;

    // Update fullscreen modal too (optional)
    const modalImg = document.getElementById("lightbox-img");
    if (modalImg) modalImg.src = images[currentIndex].file;
}

function nextImage() {
    if (images.length === 0) return;
    currentIndex = (currentIndex + 1) % images.length;
    updateCarousel();
}

function prevImage() {
    if (images.length === 0) return;
    currentIndex = (currentIndex - 1 + images.length) % images.length;
    updateCarousel();
}

// Initialize carousel only if it exists
document.addEventListener("DOMContentLoaded", () => {
    if (exists("#carousel-image")) {
        updateCarousel();
    }
});



// ---------------------------------------------------------
// 4. FULLSCREEN LIGHTBOX VIEWER
// ---------------------------------------------------------

function openLightbox() {
    const modal = document.getElementById("lightbox");
    const modalImg = document.getElementById("lightbox-img");

    if (!modal || !modalImg) return;

    modalImg.src = images[currentIndex]?.file || "";
    modal.style.display = "flex";
}

function closeLightbox(event) {
    event?.stopPropagation();
    const modal = document.getElementById("lightbox");
    if (modal) modal.style.display = "none";
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
