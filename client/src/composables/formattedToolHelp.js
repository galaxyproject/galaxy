import { computed, unref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

/**
 * Increase the heading levels of all child nodes of a node
 * @param {HTMLElement} node
 * @param {number} increaseBy
 */
function increaseHeadingLevels(node, increaseBy) {
    [5, 4, 3, 2, 1].forEach((level) => {
        increaseHeadingLevel(node, level, increaseBy);
    });
}

/**
 * Increase a single heading level
 */
function increaseHeadingLevel(node, level, increaseBy) {
    // cap target level at 6 (highest heading level)
    let targetLevel = level + increaseBy;
    if (targetLevel > 6) {
        targetLevel = 6;
    }

    const headings = node.getElementsByTagName(`h${level}`);

    // create new headings with target level and copy contents + attributes
    Array.from(headings).forEach((heading) => {
        const newTag = heading.ownerDocument.createElement(`h${targetLevel}`);
        newTag.innerHTML = heading.innerHTML;

        Array.from(heading.attributes).forEach((attribute) => {
            newTag.setAttribute(attribute.name, attribute.value);
        });

        heading.insertAdjacentElement("beforebegin", newTag);
        heading.remove();
    });
}

// Scheme, path-absolute, query or fragment: not relative to the tool.
const NOT_TOOL_RELATIVE = /^([a-z][a-z0-9+.-]*:|[/#?])/i;

function isToolRelativePath(src) {
    return !!src && !NOT_TOOL_RELATIVE.test(src);
}

function decodePath(src) {
    const path = src.split(/[?#]/)[0];
    try {
        return decodeURIComponent(path);
    } catch {
        return path;
    }
}

function toolHelpImageUrl(tool, src) {
    const params = new URLSearchParams({ path: decodePath(src) });
    if (tool.version) {
        params.set("tool_version", tool.version);
    }
    return `${getAppRoot()}api/tools/${encodeURIComponent(tool.id)}/help_image?${params}`;
}

/**
 * @param helpContent help HTML
 * @param {{ tool?: import("vue").MaybeRef<{ id?: string, version?: string }>, headingLevelIncrease?: number }} [options]
 *     `tool` serves images with relative paths from that tool's directory
 */
export function useFormattedToolHelp(helpContent, { tool, headingLevelIncrease = 2 } = {}) {
    const formattedContent = computed(() => {
        // DOMParser gives an inert document, so nothing in the help loads before it is sanitized
        const node = new DOMParser().parseFromString(unref(helpContent), "text/html").body;

        const links = node.getElementsByTagName("a");
        Array.from(links).forEach((link) => {
            if (!link.getAttribute("href")?.startsWith("#")) {
                link.target = "_blank";
            }
        });

        const toolValue = unref(tool);
        const images = node.getElementsByTagName("img");
        Array.from(images).forEach((image) => {
            const src = image.getAttribute("src");
            if (image.src.includes("admin_toolshed")) {
                image.src = getAppRoot() + image.src;
            } else if (toolValue?.id && isToolRelativePath(src)) {
                image.src = toolHelpImageUrl(toolValue, src);
            }
        });

        increaseHeadingLevels(node, unref(headingLevelIncrease));

        return node.innerHTML;
    });

    return { formattedContent };
}
