import { computed, unref } from "vue";
import { getAppRoot } from "onload/loadConfig";

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
        const newTag = document.createElement(`h${targetLevel}`);
        newTag.innerHTML = heading.innerHTML;

        Array.from(heading.attributes).forEach((attribute) => {
            newTag.setAttribute(attribute.name, attribute.value);
        });

        heading.insertAdjacentElement("beforebegin", newTag);
        heading.remove();
    });
}

export function useFormattedToolHelp(helpContent, headingLevelIncrease = 2) {
    const formattedContent = computed(() => {
        const node = document.createElement("div");
        node.innerHTML = unref(helpContent);

        const links = node.getElementsByTagName("a");
        Array.from(links).forEach((link) => {
            link.target = "_blank";
        });

        const images = node.getElementsByTagName("img");
        Array.from(images).forEach((image) => {
            if (image.src.includes("admin_toolshed")) {
                image.src = getAppRoot() + image.src;
            }
        });

        increaseHeadingLevels(node, unref(headingLevelIncrease));

        return node.innerHTML;
    });

    return { formattedContent };
}
