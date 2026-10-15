/**
 * DOMPurify profiles shared by the `v-sanitize-html` directive and any code that
 * needs a cleaned HTML string directly.
 *
 * Profiles:
 *   default  -- DOMPurify's HTML profile (no SVG/MathML), without <style>
 *               or form controls.
 *   links    -- default, plus `target` is kept; a target that opens a new
 *               window also gets `rel="noopener noreferrer"`.
 *   markdown -- links, plus what Galaxy markdown renders: KaTeX's SVG and
 *               MathML, the gxhelp:/gxstatic:/gxdatasetasimage: URIs that
 *               useGxUris and the help popovers rewrite after render, and the
 *               buttons the authoring help adds.
 */

import purify, { type Config, type DOMPurify } from "dompurify";

export type SanitizeHtmlProfile = "default" | "links" | "markdown";

// Rendered content never needs these: a <style> element restyles the whole
// page, and form controls belong in Galaxy's own components.
const FORM_TAGS = ["form", "input", "button", "textarea", "select"];

const HTML_ONLY: Config = { USE_PROFILES: { html: true }, FORBID_TAGS: ["style", ...FORM_TAGS] };

// DOMPurify's default URI allow-list with Galaxy's internal schemes added.
const GALAXY_URI_REGEXP =
    /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix|gxhelp|gxstatic|gxdatasetasimage):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i;

export const PROFILE_CONFIGS: Record<SanitizeHtmlProfile, Config> = {
    default: HTML_ONLY,
    links: { ...HTML_ONLY, ADD_ATTR: ["target"] },
    markdown: {
        USE_PROFILES: { html: true, svg: true, mathMl: true },
        FORBID_TAGS: ["style"],
        // KaTeX wraps its MathML in <semantics> with the TeX source in <annotation>
        ADD_TAGS: ["semantics", "annotation"],
        ADD_ATTR: ["target"],
        ALLOWED_URI_REGEXP: GALAXY_URI_REGEXP,
    },
};

const REQUIRED_REL = ["noopener", "noreferrer"];
// These navigate a window that already exists, so there is no new opener to cut off.
const SAME_WINDOW_TARGETS = ["_self", "_top", "_parent"];

// Hooks are registered per DOMPurify instance, so the profiles that keep
// `target` get their own instance -- otherwise the rel hook would also run for
// every other `purify.sanitize` caller in the client.
let targetPurifier: DOMPurify | null = null;

function getTargetPurifier(): DOMPurify {
    if (!targetPurifier) {
        targetPurifier = purify(window);
        targetPurifier.addHook("afterSanitizeAttributes", (node) => {
            const element = node as Element;
            const target = node.nodeType === Node.ELEMENT_NODE ? element.getAttribute("target")?.toLowerCase() : null;
            if (target && !SAME_WINDOW_TARGETS.includes(target)) {
                const rel = new Set((element.getAttribute("rel") || "").split(/\s+/).filter(Boolean));
                REQUIRED_REL.forEach((value) => rel.add(value));
                element.setAttribute("rel", Array.from(rel).join(" "));
            }
        });
    }
    return targetPurifier;
}

/** Clean an HTML string with the named profile; the result can be assigned to `innerHTML`. */
export function sanitizeHtml(html: string | null | undefined, profile: SanitizeHtmlProfile = "default"): string {
    const config = PROFILE_CONFIGS[profile];
    if (!config) {
        throw new Error(`Unknown v-sanitize-html profile: ${profile}`);
    }
    const purifier = profile === "default" ? purify : getTargetPurifier();
    return purifier.sanitize(html ?? "", config);
}
