// Guided report walkthrough: step navigation and self-reported review checkmarks.
// Session-only by design: no storage, no cookies, no network, no submission.
(() => {
  "use strict";
  const steps = Array.from(document.querySelectorAll("[data-walk-step]"));
  const checks = Array.from(document.querySelectorAll("[data-review-check]"));
  const prev = document.getElementById("walk-prev");
  const next = document.getElementById("walk-next");
  const progress = document.getElementById("walk-progress");
  const status = document.getElementById("walk-status");
  const counter = document.getElementById("walk-step-count");
  const complete = document.getElementById("walk-complete");
  if (!steps.length || !prev || !next || !progress || !status) return;

  let current = 0;
  const reviewed = new Set();

  function render(moveFocus) {
    steps.forEach((section, index) => {
      section.hidden = index !== current;
    });
    prev.disabled = current === 0;
    next.disabled = current === steps.length - 1;
    progress.value = reviewed.size;
    progress.textContent = reviewed.size + " of " + steps.length;
    if (counter) counter.textContent = String(current + 1);
    status.textContent = reviewed.size + " of " + steps.length +
      " exercises marked reviewed. Nothing has been submitted.";
    if (complete) complete.hidden = reviewed.size !== steps.length;
    if (moveFocus) {
      const heading = steps[current].querySelector("h2");
      if (heading) heading.focus();
    }
  }

  checks.forEach((check) => {
    check.addEventListener("change", () => {
      const section = check.closest("[data-walk-step]");
      const index = section ? steps.indexOf(section) : -1;
      if (index < 0) return;
      if (check.checked) reviewed.add(index);
      else reviewed.delete(index);
      render(false);
    });
  });

  prev.addEventListener("click", () => {
    if (current === 0) return;
    current -= 1;
    render(true);
  });
  next.addEventListener("click", () => {
    if (current >= steps.length - 1) return;
    current += 1;
    render(true);
  });

  render(false);
})();
