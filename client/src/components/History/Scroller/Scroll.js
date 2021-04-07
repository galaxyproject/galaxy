function inserted(el, binding) {
    const { self = false } = binding.modifiers || {};
    const value = binding.value;

    const options = (typeof value === "object" && value.options) || {
        passive: true,
    };

    const handler = typeof value === "function" || "handleEvent" in value ? value : value.handler;

    const target = self ? el : binding.arg ? document.querySelector(binding.arg) : window;

    if (!target) return;

    target.addEventListener("scroll", handler, options);

    el._onScroll = {
        handler,
        options,
        // Don't reference self
        target: self ? undefined : target,
    };
}

function unbind(el) {
    if (!el._onScroll) return;
    const { handler, target = el } = el._onScroll;
    target.removeEventListener("scroll", handler);
    delete el._onScroll;
}

export const Scroll = {
    inserted,
    unbind,
};

export default Scroll;
