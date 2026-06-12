/* ============================================================================
 * expandable-tabs.js — active-state helper for the ported nav tabs.
 * Toggles `.active` on in-page section anchors (landing page) as you scroll.
 * Hover/active expansion itself is pure CSS; path-based active state for app
 * pages is set server-side via Jinja.
 *
 * Uses a reference-line scroll-spy (not a center band) so that short sections
 * activate correctly, and treats a click as explicit intent: the clicked tab
 * stays active until the user scrolls themselves — otherwise clicking a small
 * section (e.g. "Fields") would immediately snap the highlight to the next one.
 * ========================================================================== */
(function () {
  const spyTabs = Array.prototype.slice.call(document.querySelectorAll(".nav-tab[data-spy]"));
  if (!spyTabs.length) return;

  const items = spyTabs
    .map((tab) => ({ tab, sec: document.querySelector(tab.getAttribute("data-spy")) }))
    .filter((x) => x.sec);
  if (!items.length) return;

  const OFFSET = 110; // reference line, px below the top of the viewport
  let ticking = false;
  let lock = false; // paused after a click until the user scrolls again

  const setActive = (tab) => spyTabs.forEach((t) => t.classList.toggle("active", t === tab));

  function update() {
    ticking = false;
    if (lock) return;

    const line = window.scrollY + OFFSET;
    let current = null;
    for (let i = 0; i < items.length; i++) {
      const top = items[i].sec.getBoundingClientRect().top + window.scrollY;
      if (top - 1 <= line) current = items[i];
      else break;
    }
    // At the very bottom, force the last section (it may be too short to reach the line)
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {
      current = items[items.length - 1];
    }
    // Above the first section (hero / top of page) nothing is "current" → no active tab
    setActive(current ? current.tab : null);
  }

  function onScroll() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(update);
    }
  }

  // Click = explicit intent: highlight it and pause the spy until a real scroll.
  items.forEach((it) =>
    it.tab.addEventListener("click", () => {
      setActive(it.tab);
      lock = true;
    }),
  );
  ["wheel", "touchstart", "keydown"].forEach((ev) =>
    window.addEventListener(ev, () => (lock = false), { passive: true }),
  );

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  update();
})();
