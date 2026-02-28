import { arrow, autoUpdate, computePosition, flip, offset, type Placement, shift } from "@floating-ui/dom";

interface TooltipState {
    tooltipEl: HTMLDivElement | null;
    arrowEl: HTMLDivElement | null;
    cleanup: (() => void) | null;
    listeners: Array<[string, EventListener]>;
    showing: boolean;
    text: string;
    placement: Placement;
    noninteractive: boolean;
    useHtml: boolean;
    danger: boolean;
}

const stateMap = new WeakMap<HTMLElement, TooltipState>();

let stylesInjected = false;

function injectStyles() {
    if (stylesInjected) {
        return;
    }

    stylesInjected = true;

    const style = document.createElement("style");
    style.setAttribute("data-g-tooltip-directive", "");
    style.textContent = `
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
.g-tooltip-d:not(.sr-only) {
    display: block;
}
.g-tooltip-d.g-tooltip-danger {
    background-color: var(--color-red-700, #dc3545);
}
.g-tooltip-d .g-tooltip-arrow {
    visibility: hidden;
}
.g-tooltip-d .g-tooltip-arrow,
.g-tooltip-d .g-tooltip-arrow::before {
    position: absolute;
    width: 8px;
    height: 8px;
    background: inherit;
    z-index: -1;
    top: 0;
    left: 0;
}
.g-tooltip-d .g-tooltip-arrow::before {
    visibility: visible;
    content: "";
    transform: rotate(45deg);
}
.g-tooltip-d .g-tooltip-arrow[data-placement^="top"] {
    top: unset;
    bottom: -4px;
}
.g-tooltip-d .g-tooltip-arrow[data-placement^="bottom"] {
    top: -4px;
    bottom: unset;
}
.g-tooltip-d .g-tooltip-arrow[data-placement^="left"] {
    left: unset;
    right: -4px;
}
.g-tooltip-d .g-tooltip-arrow[data-placement^="right"] {
    left: -4px;
    right: unset;
}
`;
    document.head.appendChild(style);
}

function getPlacementFromModifiers(modifiers: Record<string, boolean>): Placement {
    if (modifiers.bottom) {
        return "bottom";
    }

    if (modifiers.left) {
        return "left";
    }

    if (modifiers.right) {
        return "right";
    }

    return "top";
}

function resolveText(el: HTMLElement, value: unknown, existingText: string): string {
    if (typeof value === "string" && value) {
        return value;
    }

    if (value && typeof value === "object" && "title" in value && (value as { title: string }).title) {
        return (value as { title: string }).title;
    }

    const titleAttr = el.getAttribute("title");

    if (titleAttr) {
        return titleAttr;
    }

    return existingText;
}

function resolvePlacement(value: unknown, modifiers: Record<string, boolean>): Placement {
    if (value && typeof value === "object" && "placement" in value) {
        return (value as { placement: Placement }).placement;
    }

    return getPlacementFromModifiers(modifiers);
}

function createTooltipEl(state: TooltipState): HTMLDivElement {
    injectStyles();

    const tooltip = document.createElement("div");
    tooltip.setAttribute("role", "tooltip");
    tooltip.className = "g-tooltip-d sr-only";

    if (state.danger) {
        tooltip.classList.add("g-tooltip-danger");
    }

    if (!state.noninteractive) {
        tooltip.style.pointerEvents = "auto";
    }

    const arrowDiv = document.createElement("div");
    arrowDiv.className = "g-tooltip-arrow";
    tooltip.appendChild(arrowDiv);

    state.arrowEl = arrowDiv;
    document.body.appendChild(tooltip);

    return tooltip;
}

function updateContent(state: TooltipState) {
    if (!state.tooltipEl || !state.arrowEl) {
        return;
    }

    // Remove all children except arrow
    while (state.tooltipEl.firstChild && state.tooltipEl.firstChild !== state.arrowEl) {
        state.tooltipEl.removeChild(state.tooltipEl.firstChild);
    }

    if (state.useHtml) {
        const wrapper = document.createElement("span");
        wrapper.innerHTML = state.text;
        state.tooltipEl.insertBefore(wrapper, state.arrowEl);
    } else {
        const textNode = document.createTextNode(state.text);
        state.tooltipEl.insertBefore(textNode, state.arrowEl);
    }
}

async function updatePosition(el: HTMLElement, state: TooltipState) {
    if (!state.tooltipEl || !state.arrowEl) {
        return;
    }

    const { x, y, middlewareData, placement } = await computePosition(el, state.tooltipEl, {
        placement: state.placement,
        middleware: [
            offset(8),
            flip({ altBoundary: true }),
            shift({ altBoundary: true }),
            arrow({ element: state.arrowEl }),
        ],
    });

    state.tooltipEl.style.transform = `translate(${x}px, ${y}px)`;

    if (middlewareData.arrow) {
        const { x: ax, y: ay } = middlewareData.arrow;
        state.arrowEl.style.transform = `translate(${ax ?? 0}px, ${ay ?? 0}px)`;
    }

    state.arrowEl.setAttribute("data-placement", placement);
}

function show(el: HTMLElement, state: TooltipState) {
    if (state.showing || !state.text) {
        return;
    }

    if (el.hasAttribute("disabled") || el.getAttribute("aria-disabled") === "true") {
        return;
    }

    state.showing = true;

    if (!state.tooltipEl) {
        state.tooltipEl = createTooltipEl(state);
    }

    updateContent(state);
    state.tooltipEl.classList.remove("sr-only");
    state.tooltipEl.setAttribute("data-show", "true");

    state.cleanup = autoUpdate(el, state.tooltipEl, () => updatePosition(el, state));
}

function hide(_el: HTMLElement, state: TooltipState) {
    if (!state.showing) {
        return;
    }

    state.showing = false;
    state.cleanup?.();
    state.cleanup = null;

    if (state.tooltipEl) {
        state.tooltipEl.classList.add("sr-only");
        state.tooltipEl.removeAttribute("data-show");
    }
}

function setupListeners(el: HTMLElement, state: TooltipState, modifiers: Record<string, boolean>) {
    for (const [event, handler] of state.listeners) {
        el.removeEventListener(event, handler);
    }

    state.listeners = [];

    const focusOnly = modifiers.focus && !modifiers.hover;
    const showHandler = () => show(el, state);
    const hideHandler = () => hide(el, state);
    const keyHandler = (e: Event) => {
        if ((e as KeyboardEvent).key === "Escape") {
            hide(el, state);
        }
    };

    if (focusOnly) {
        el.addEventListener("focusin", showHandler);
        el.addEventListener("focusout", hideHandler);
        state.listeners.push(["focusin", showHandler], ["focusout", hideHandler]);
    } else {
        // Default: hover + focus for accessibility
        el.addEventListener("mouseenter", showHandler);
        el.addEventListener("mouseleave", hideHandler);
        el.addEventListener("focus", showHandler);
        el.addEventListener("blur", hideHandler);
        state.listeners.push(
            ["mouseenter", showHandler],
            ["mouseleave", hideHandler],
            ["focus", showHandler],
            ["blur", hideHandler],
        );
    }

    el.addEventListener("keydown", keyHandler);
    state.listeners.push(["keydown", keyHandler]);
}

function destroyTooltip(state: TooltipState) {
    state.cleanup?.();
    state.cleanup = null;

    if (state.tooltipEl) {
        state.tooltipEl.remove();
        state.tooltipEl = null;
        state.arrowEl = null;
    }
}

function inserted(el: HTMLElement, binding: { value?: unknown; modifiers: Record<string, boolean> }) {
    const modifiers = binding.modifiers || {};
    const text = resolveText(el, binding.value, "");

    const state: TooltipState = {
        tooltipEl: null,
        arrowEl: null,
        cleanup: null,
        listeners: [],
        showing: false,
        text,
        placement: resolvePlacement(binding.value, modifiers),
        noninteractive: !!modifiers.noninteractive,
        useHtml: !!modifiers.html,
        danger: !!modifiers["v-danger"],
    };

    // Remove title attribute to prevent native browser tooltip
    if (el.hasAttribute("title")) {
        el.removeAttribute("title");
    }

    stateMap.set(el, state);
    setupListeners(el, state, modifiers);
}

function componentUpdated(el: HTMLElement, binding: { value?: unknown; modifiers: Record<string, boolean> }) {
    const state = stateMap.get(el);

    if (!state) {
        return;
    }

    const modifiers = binding.modifiers || {};
    const newText = resolveText(el, binding.value, state.text);

    if (el.hasAttribute("title")) {
        el.removeAttribute("title");
    }

    state.text = newText;
    state.placement = resolvePlacement(binding.value, modifiers);
    state.danger = !!modifiers["v-danger"];

    if (state.tooltipEl) {
        updateContent(state);

        if (state.danger) {
            state.tooltipEl.classList.add("g-tooltip-danger");
        } else {
            state.tooltipEl.classList.remove("g-tooltip-danger");
        }
    }

    // Hide if text became empty
    if (!state.text && state.showing) {
        hide(el, state);
    }
}

function unbind(el: HTMLElement) {
    const state = stateMap.get(el);

    if (!state) {
        return;
    }

    for (const [event, handler] of state.listeners) {
        el.removeEventListener(event, handler);
    }

    destroyTooltip(state);
    stateMap.delete(el);
}

export const vGTooltip = {
    inserted,
    componentUpdated,
    unbind,
};

export default vGTooltip;
