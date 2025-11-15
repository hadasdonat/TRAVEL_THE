// פותח מודל על פי data-modal של הכפתור
document.addEventListener("DOMContentLoaded", () => {

  const buttons = document.querySelectorAll(".open-modal");
  const modals = document.querySelectorAll(".modal");
  const closes = document.querySelectorAll(".modal .close");

  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.modal;
      const modal = document.getElementById(id);
      if (modal) modal.style.display = "flex";
    });
  });

  closes.forEach(x => {
    x.addEventListener("click", () => {
      x.closest(".modal").style.display = "none";
    });
  });

  window.addEventListener("click", e => {
    modals.forEach(m => {
      if (e.target === m) m.style.display = "none";
    });
  });

  window.addEventListener("keydown", e => {
    if (e.key === "Escape") {
      modals.forEach(m => m.style.display = "none");
    }
  });

});
