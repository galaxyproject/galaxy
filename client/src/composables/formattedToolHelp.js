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

// Prefixes of image paths the server already routed for Tool Shed RST help.
const SHED_IMAGE_ROUTES = ["admin_toolshed/", "shed_tool_static/"];

function isToolRelativePath(src) {
    return (
        !!src && !/^([a-z][a-z0-9+.-]*:|[/#?])/i.test(src) && !SHED_IMAGE_ROUTES.some((route) => src.startsWith(route))
    );
}

function decodePath(src) {
    try {
        return decodeURIComponent(src);
    } catch {
        return src;
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
 * @param headingLevelIncrease how many levels to demote headings
 * @param {import("vue").MaybeRef<{ id?: string, version?: string }>} [tool] images with relative paths are served from this tool's directory
 */
export function useFormattedToolHelp(helpContent, headingLevelIncrease = 2, tool) {
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
