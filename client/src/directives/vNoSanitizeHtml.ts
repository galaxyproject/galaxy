/**
 * Sets `innerHTML` without cleaning it. This is the named alternative to raw
 * `v-html` for the rare content that only the Galaxy server, shipped client
 * code or the operator's config files can produce and that DOMPurify would
 * alter (see `v-sanitize-html` for everything else). Admin-only content entered
 * through the UI still goes through `v-sanitize-html`.
 *
 * Every use needs an HTML comment directly above it explaining where the
 * content comes from and why `v-sanitize-html` does not fit, so reviewers can
 * judge the claim.
 */

import type { DirectiveBinding, ObjectDirective } from "vue";

type NoSanitizeHtmlBinding = string | null | undefined;

export const vNoSanitizeHtml: ObjectDirective<HTMLElement, NoSanitizeHtmlBinding> = {
    bind(el, binding: DirectiveBinding<NoSanitizeHtmlBinding>) {
        el.innerHTML = binding.value ?? "";
    },
    update(el, binding: DirectiveBinding<NoSanitizeHtmlBinding>) {
        if (binding.value !== binding.oldValue) {
            el.innerHTML = binding.value ?? "";
        }
    },
};

export default vNoSanitizeHtml;
