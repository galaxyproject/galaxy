/**
 * Custom tooltip directive to replace bootstrap-vue's v-b-tooltip.
 * Uses @floating-ui/dom for positioning (same library as GTooltip component).
 *
 * Supports the same modifier API as v-b-tooltip:
 *   Placement: .top (default), .bottom, .left, .right, .topright
 *   Trigger:   .hover (default), .focus
 *   Content:   .html (innerHTML instead of textContent)
 *   Compat:    .noninteractive, .nofade (accepted, no-op — all tooltips are noninteractive)
 *   Styling:   .v-danger
 *
 * Value forms:
 *   v-g-tooltip                           → reads element's title attribute
 *   v-g-tooltip="'text'"                  → string content
 *   v-g-tooltip="{ title, placement }"    → object config (title optional, falls back to :title)
 */

import {
    arrow as arrowMiddleware,
    autoUpdate,
    computePosition,
    flip,
    offset,
    type Placement,
    shift,
} from "@floating-ui/dom";
import type { DirectiveOptions } from "vue";

interface TooltipState {
    tooltipEl: HTMLElement;
    arrowEl: HTMLElement;
    contentEl: HTMLElement;
    cleanupAutoUpdate: (() => void) | null;
    cleanupListeners: () => void;
    placement: Placement;
    isHtml: boolean;
}

const stateMap = new WeakMap<HTMLElement, TooltipState>();

let tooltipCounter = 0;
let stylesInjected = false;

const TOOLTIP_STYLES = `
.g-tooltip-d {
    background-color: var(--color-blue-800);
    color: var(--color-grey-100);
    padding: var(--spacing-1) var(--spacing-2);
    font-size: var(--font-size-small);
    border-radius: var(--spacing-1);
    pointer-events: none;
    font-weight: 400;
    z-index: 9999;
    width: max-content;
    max-width: 300px;
    position: absolute;
    top: 0;
    left: 0;
}
.g-tooltip-d.g-tooltip-danger {
    background-color: var(--color-red-700, #dc3545);
}
.g-tooltip-d .g-tooltip-d-arrow,
.g-tooltip-d .g-tooltip-d-arrow::before {
    position: absolute;
    width: 8px;
    height: 8px;
    background: inherit;
    z-index: -1;
    top: 0;
    left: 0;
}
.g-tooltip-d .g-tooltip-d-arrow {
    visibility: hidden;
}
.g-tooltip-d .g-tooltip-d-arrow::before {
    visibility: visible;
    content: "";
    transform: rotate(45deg);
}
.g-tooltip-d .g-tooltip-d-arrow[data-placement^="top"] {
    top: unset;
    bottom: -4px;
}
.g-tooltip-d .g-tooltip-d-arrow[data-placement^="bottom"] {
    top: -4px;
    bottom: unset;
}
.g-tooltip-d .g-tooltip-d-arrow[data-placement^="left"] {
    left: unset;
    right: -4px;
}
.g-tooltip-d .g-tooltip-d-arrow[data-placement^="right"] {
    left: -4px;
    right: unset;
}
`;

const PLACEMENT_MAP: Record<string, Placement> = {
    top: "top",
    bottom: "bottom",
    left: "left",
    right: "right",
    topright: "top-end",
    topleft: "top-start",
    bottomright: "bottom-end",
    bottomleft: "bottom-start",
};

function injectStyles() {
    if (stylesInjected) {
        return;
    }
    stylesInjected = true;
    const style = document.createElement("style");
    style.textContent = TOOLTIP_STYLES;
    document.head.appendChild(style);
}

function getPlacement(modifiers: Record<string, boolean>, bindingValue: unknown): Placement {
    for (const [mod, placement] of Object.entries(PLACEMENT_MAP)) {
        if (modifiers[mod]) {
            return placement;
        }
    }
    if (typeof bindingValue === "object" && bindingValue !== null && "placement" in bindingValue) {
        return (bindingValue as { placement: Placement }).placement;
    }
    return "top";
}

function getContent(el: HTMLElement, bindingValue: unknown): string {
    if (typeof bindingValue === "string" && bindingValue) {
        return bindingValue;
    }
    if (typeof bindingValue === "object" && bindingValue !== null && "title" in bindingValue) {
        return String((bindingValue as { title: string }).title || "");
    }
    // Fall back to element's title attribute; capture and remove it to prevent native tooltip
    const title = el.getAttribute("title");
    if (title) {
        el.removeAttribute("title");
        el.dataset.gTooltipTitle = title;
    }
    return el.dataset.gTooltipTitle || "";
}

function createTooltipEl(isDanger: boolean): { tooltipEl: HTMLElement; arrowEl: HTMLElement; contentEl: HTMLElement } {
    injectStyles();
    const tooltipEl = document.createElement("div");
    tooltipEl.setAttribute("role", "tooltip");
    // "tooltip" class matches bootstrap-vue's rendered element for Selenium selector compat
    tooltipEl.className = "tooltip g-tooltip-d";
    if (isDanger) {
        tooltipEl.classList.add("g-tooltip-danger");
    }

    // "tooltip-inner" matches bootstrap-vue's inner element for Selenium selector compat
    const contentEl = document.createElement("div");
    contentEl.className = "tooltip-inner";
    tooltipEl.appendChild(contentEl);

    const arrowEl = document.createElement("div");
    arrowEl.className = "g-tooltip-d-arrow";
    tooltipEl.appendChild(arrowEl);

    // Don't append to body yet — add on show, remove on hide,
    // so Selenium wait_for_absent(".tooltip") works correctly
    return { tooltipEl, arrowEl, contentEl };
}

async function updatePosition(el: HTMLElement, state: TooltipState) {
    const { x, y, middlewareData, placement } = await computePosition(el, state.tooltipEl, {
        placement: state.placement,
        middleware: [
            offset(8),
            flip({ altBoundary: true }),
            shift({ altBoundary: true }),
            arrowMiddleware({ element: state.arrowEl }),
        ],
    });

    state.tooltipEl.style.transform = `translate(${x}px, ${y}px)`;

    if (middlewareData.arrow) {
        const ax = middlewareData.arrow.x ?? 0;
        const ay = middlewareData.arrow.y ?? 0;
        state.arrowEl.style.transform = `translate(${ax}px, ${ay}px)`;
    }

    state.arrowEl.dataset.placement = placement;
}

function showTooltip(el: HTMLElement) {
    const state = stateMap.get(el);
    if (!state) {
        return;
    }

    if (
        (el as HTMLButtonElement).disabled ||
        el.getAttribute("disabled") === "true" ||
        el.getAttribute("aria-disabled") === "true"
    ) {
        return;
    }

    const content = state.isHtml ? state.contentEl.innerHTML : state.contentEl.textContent;
    if (!content) {
        return;
    }

    if (!state.tooltipEl.isConnected) {
        document.body.appendChild(state.tooltipEl);
    }

    state.cleanupAutoUpdate = autoUpdate(el, state.tooltipEl, () => updatePosition(el, state));
}

function hideTooltip(el: HTMLElement) {
    const state = stateMap.get(el);
    if (!state) {
        return;
    }

    state.cleanupAutoUpdate?.();
    state.cleanupAutoUpdate = null;

    if (state.tooltipEl.isConnected) {
        state.tooltipEl.remove();
    }
}

function setupListeners(el: HTMLElement, modifiers: Record<string, boolean>, arg?: string): () => void {
    const listeners: Array<[string, EventListener]> = [];

    function addListener(event: string, handler: EventListener) {
        el.addEventListener(event, handler);
        listeners.push([event, handler]);
    }

    const focusOnly = (modifiers.focus || arg === "focus") && !modifiers.hover && arg !== "hover";
    const showHandler = () => showTooltip(el);
    const hideHandler = () => hideTooltip(el);
    const keyHandler = (e: Event) => {
        if ((e as KeyboardEvent).key === "Escape") {
            hideTooltip(el);
        }
    };

    if (!focusOnly) {
        addListener("mouseenter", showHandler);
        addListener("mouseleave", hideHandler);
    }
    addListener("focusin", showHandler);
    addListener("focusout", hideHandler);
    addListener("keydown", keyHandler);

    return () => {
        for (const [event, handler] of listeners) {
            el.removeEventListener(event, handler);
        }
    };
}

function sanitizeHtml(raw: string): string {
    const doc = new DOMParser().parseFromString(raw, "text/html");
    doc.querySelectorAll("script,style,iframe,object,embed,form").forEach((el) => el.remove());
    return doc.body.innerHTML;
}

function updateContent(el: HTMLElement, bindingValue: unknown, state: TooltipState) {
    const content = getContent(el, bindingValue);
    if (state.isHtml) {
        state.contentEl.innerHTML = sanitizeHtml(content);
    } else {
        state.contentEl.textContent = content;
    }
}

export const vGTooltip: DirectiveOptions = {
    inserted(el, binding) {
        const modifiers = binding.modifiers || {};
        const isDanger = !!modifiers["v-danger"];
        const isHtml = !!modifiers.html;
        const placement = getPlacement(modifiers, binding.value);

        const { tooltipEl, arrowEl, contentEl } = createTooltipEl(isDanger);
        const cleanupListeners = setupListeners(el, modifiers, binding.arg);

        const uid = `g-tooltip-${tooltipCounter++}`;
        tooltipEl.id = uid;
        el.setAttribute("aria-describedby", uid);

        const state: TooltipState = {
            tooltipEl,
            arrowEl,
            contentEl,
            cleanupAutoUpdate: null,
            cleanupListeners,
            placement,
            isHtml,
        };

        stateMap.set(el, state);
        updateContent(el, binding.value, state);
    },

    componentUpdated(el, binding) {
        const state = stateMap.get(el);
        if (!state) {
            return;
        }
        updateContent(el, binding.value, state);
        state.placement = getPlacement(binding.modifiers || {}, binding.value);

        // Hide if content became empty
        const content = state.isHtml ? state.contentEl.innerHTML : state.contentEl.textContent;
        if (!content && state.tooltipEl.isConnected) {
            hideTooltip(el);
        }
    },

    unbind(el) {
        const state = stateMap.get(el);
        if (!state) {
            return;
        }
        state.cleanupListeners();
        state.cleanupAutoUpdate?.();
        state.tooltipEl.remove();
        el.removeAttribute("aria-describedby");
        stateMap.delete(el);
    },
};

export default vGTooltip;
