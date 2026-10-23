/* Pittsburgh Chimney Sweeps: shared behavior. Every feature is opt-in by markup,
   so a page only gets what it contains. window.SITE is injected by build.mjs. */
(function () {
  const SITE = window.SITE || {};
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const root = document.body.dataset.root || "";
  const store = {
    get(k) { try { return JSON.parse(sessionStorage.getItem(k) || "null"); } catch (_) { return null; } },
    set(k, v) { try { sessionStorage.setItem(k, JSON.stringify(v)); } catch (_) {} },
    del(k) { try { sessionStorage.removeItem(k); } catch (_) {} },
  };
  document.documentElement.classList.add("js");
  $$("[data-year]").forEach(el => (el.textContent = new Date().getFullYear()));

  // Mobile menu
  const menuBtn = $("#menuBtn"), mnav = $("#mnav");
  if (menuBtn && mnav) {
    menuBtn.addEventListener("click", () => {
      const open = mnav.hidden;
      mnav.hidden = !open;
      menuBtn.setAttribute("aria-expanded", String(open));
    });
    $$("a", mnav).forEach(a => a.addEventListener("click", () => { mnav.hidden = true; menuBtn.setAttribute("aria-expanded", "false"); }));
  }

  // Services dropdown: hover/focus is CSS; the chevron button toggles for touch and keyboard
  $$(".nav-dd").forEach(dd => {
    const btn = $(".dd-btn", dd);
    if (!btn) return;
    btn.addEventListener("click", e => {
      e.stopPropagation();
      const open = !dd.classList.contains("open");
      dd.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("click", e => { if (!dd.contains(e.target)) { dd.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); } });
    dd.addEventListener("keydown", e => { if (e.key === "Escape") { dd.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); btn.focus(); } });
  });

  // Tabs: <div role="tablist"> with role="tab" buttons whose aria-controls name role="tabpanel" elements
  $$('[role="tablist"]').forEach(list => {
    const tabs = $$('[role="tab"]', list);
    const select = t => tabs.forEach(x => {
      const on = x === t;
      x.setAttribute("aria-selected", String(on));
      x.tabIndex = on ? 0 : -1;
      const p = document.getElementById(x.getAttribute("aria-controls"));
      if (p) p.hidden = !on;
    });
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => select(t));
      t.addEventListener("keydown", e => {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        const n = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
        select(n); n.focus();
      });
    });
  });

  // Warning-sign self-check: [data-checker] containing .signs checkboxes (value = weight; 3 = urgent) and a .verdict
  $$("[data-checker]").forEach(box => {
    const verdicts = [
      { t: "Looking good so far", p: "Tick any signs that apply. If none do, keep enjoying your fireplace and book your annual sweep before burning season.", c: "Book annual sweep" },
      { t: "Time for a check-up", p: "Nothing alarming, but it's worth a sweep and Level 1 inspection before your next fire. Most visits take under 90 minutes.", c: "Book a sweep" },
      { t: "Get it looked at soon", p: "Those signs point to buildup, moisture or masonry wear. We recommend a sweep with a camera inspection so nothing gets missed.", c: "Book an inspection" },
      { t: "Don't light a fire yet", p: "Water entry or signs of a past chimney fire can hide serious damage. Hold off burning and let us take a look. Call for the earliest opening.", c: "Call for priority visit" },
    ];
    const verdict = $(".verdict", box), bars = $$(".meter i", box), cta = $("[data-verdict-cta]", box);
    box.addEventListener("change", () => {
      const checked = $$(".signs input:checked", box);
      const score = checked.reduce((s, i) => s + Number(i.value), 0);
      const urgent = checked.some(i => i.value === "3");
      const level = score === 0 ? 0 : score <= 2 && !urgent ? 1 : score <= 5 && !urgent ? 2 : 3;
      const lit = Math.min(bars.length, Math.round(score / 2) + (score ? 1 : 0));
      bars.forEach((b, i) => b.classList.toggle("on", i < lit));
      verdict.dataset.level = level;
      const v = verdicts[level];
      $("[data-verdict-title]", box).textContent = v.t;
      $("[data-verdict-text]", box).textContent = v.p;
      if (cta) { cta.textContent = v.c; cta.href = level === 3 ? "tel:" + SITE.phoneTel : cta.dataset.book || root + "book.html"; }
    });
  });

  // ZIP checker: [data-zip] wrapping an input, a button and [data-zip-msg]
  function zipStatus(z) {
    if (!/^\d{5}$/.test(z)) return null;
    if (SITE.zips && SITE.zips[z]) return { s: "ok", area: SITE.zips[z] };
    const p = z.slice(0, 3);
    if ((SITE.zipServed || []).includes(p)) return { s: "ok" };
    if ((SITE.zipMaybe || []).includes(p)) return { s: "maybe" };
    return { s: "no" };
  }
  $$("[data-zip]").forEach(box => {
    const input = $("input", box), btn = $("button", box), msg = $("[data-zip-msg]", box.parentElement) || $("[data-zip-msg]");
    const check = () => {
      const z = input.value.trim(), r = zipStatus(z);
      msg.className = "zip-msg";
      if (!r) { msg.textContent = "Enter a 5-digit ZIP code."; return; }
      if (r.s === "ok") { msg.classList.add("ok"); msg.textContent = `✓ Yes, we service ${z}${r.area ? " (" + r.area + ")" : ""}. Book online or call ${SITE.phone}.`; }
      else if (r.s === "maybe") { msg.classList.add("maybe"); msg.textContent = `We often work in ${z}. Call ${SITE.phone} to confirm a date.`; }
      else { msg.classList.add("maybe"); msg.textContent = `${z} is outside our usual area, but call ${SITE.phone} and we'll see what we can do.`; }
    };
    btn.addEventListener("click", check);
    input.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); check(); } });
  });

  // Quick-book card: [data-quickbook] form. Carries details to the full booking form (same page if present, else book.html)
  $$("[data-quickbook]").forEach(f => {
    f.addEventListener("submit", e => {
      e.preventDefault();
      const zip = (f.elements.zip?.value || "").trim(), err = $(".err", f);
      if (zip && !/^\d{5}$/.test(zip)) { err.textContent = "Enter a 5-digit ZIP code."; err.hidden = false; return; }
      if (err) err.hidden = true;
      const data = { service: f.elements.service?.value, zip, phone: (f.elements.phone?.value || "").trim(), when: f.querySelector('input[name="when"]:checked')?.value };
      const target = $("[data-booking]");
      if (target) {
        prefill(target, data);
        target.closest("section")?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
        setTimeout(() => (data.phone ? target.elements.name : target.elements.phone)?.focus({ preventScroll: true }), 500);
      } else { store.set("pcs-prefill", data); location.href = root + "book.html#book"; }
    });
  });
  function prefill(form, d) {
    if (!d) return;
    const set = (n, v) => { if (v && form.elements[n]) form.elements[n].value = v; };
    if (d.service && form.elements.service && [...form.elements.service.options].some(o => o.value === d.service)) form.elements.service.value = d.service;
    set("zip", d.zip); set("phone", d.phone);
    if (d.when && d.when !== "ASAP" && form.elements.notes && !form.elements.notes.value) form.elements.notes.value = "Preferred time: " + d.when;
  }

  // Booking forms: form[data-booking]; optional data-service preselects; success swaps to the sibling [data-booking-ok]
  $$("[data-booking]").forEach(f => {
    prefill(f, store.get("pcs-prefill")); store.del("pcs-prefill");
    if (f.dataset.service && f.elements.service) {
      const opt = [...f.elements.service.options].find(o => o.value === f.dataset.service);
      if (opt) f.elements.service.value = opt.value;
    }
    const date = f.elements.date;
    if (date) date.min = new Date().toISOString().slice(0, 10);
    f.addEventListener("submit", async e => {
      e.preventDefault();
      const err = $(".err", f);
      const missing = $$("[required]", f).filter(i => !i.value.trim());
      const fail = (msg, el) => { err.textContent = msg; err.hidden = false; el?.focus(); };
      if (missing.length) return fail("Please fill in: " + missing.map(i => ($(`label[for="${i.id}"]`)?.textContent || i.name).replace(" *", "")).join(", ") + ".", missing[0]);
      if (f.elements.phone && f.elements.phone.value.replace(/\D/g, "").length < 10) return fail("Enter a 10-digit phone number.", f.elements.phone);
      if (f.elements.zip && f.elements.zip.value && !/^\d{5}$/.test(f.elements.zip.value.trim())) return fail("Enter a 5-digit ZIP code.", f.elements.zip);
      err.hidden = true;
      const btn = $('button[type="submit"]', f), label = btn.innerHTML;
      btn.disabled = true; btn.textContent = "Sending…";
      try {
        if (SITE.bookingEndpoint) {
          const fd = new FormData(f);
          fd.append("page", location.pathname);
          const res = await fetch(SITE.bookingEndpoint, { method: "POST", headers: { Accept: "application/json" }, body: fd });
          if (!res.ok) throw new Error(String(res.status));
        }
        const ok = f.parentElement.querySelector("[data-booking-ok]");
        f.hidden = true;
        if (ok) { ok.hidden = false; ok.focus?.(); }
      } catch (_) {
        fail(`We couldn't send your request. Please call or text ${SITE.phone}.`);
        btn.disabled = false; btn.innerHTML = label;
      }
    });
  });

  // Reveal on scroll: only elements below the fold start hidden, so the page is complete without JS
  if ("IntersectionObserver" in window && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const els = $$(".reveal").filter(el => el.getBoundingClientRect().top > innerHeight);
    els.forEach(el => el.classList.add("pre"));
    const io = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) { en.target.classList.remove("pre"); io.unobserve(en.target); } }), { threshold: 0.12 });
    els.forEach(el => io.observe(el));
  }
})();
