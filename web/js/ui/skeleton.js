import { el, $, clearChildren } from "../utils/dom.js";

export function renderSkeleton(count = 5) {
  const list = $("recommendationList");
  if (!list) return;
  clearChildren(list);
  const safeCount = Math.max(3, Math.min(8, Number(count) || 5));
  for (let i = 0; i < safeCount; i += 1) {
    list.appendChild(el("div", { class: "skeleton-card" }, [
      el("div", { class: "skeleton-line short" }),
      el("div", { class: "skeleton-line long" }),
      el("div", { class: "skeleton-line medium" }),
    ]));
  }
}
