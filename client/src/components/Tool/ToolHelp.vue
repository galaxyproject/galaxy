<script setup>
import { computed } from "vue";
import { getAppRoot } from "onload/loadConfig";

const props = defineProps({
    content: {
        type: String,
        required: true,
    },
});

const formattedContent = computed(() => {
    const node = document.createElement("div");
    node.innerHTML = props.content;

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

    // loop these levels backwards to avoid increasing heading twice
    [5, 4, 3, 2, 1].forEach((level) => {
        increaseHeadingLevel(node, level, 2);
    });

    return node.innerHTML;
});

/**
 * @param {HTMLElement} node
 * @param {number} level
 * @param {number} increaseBy
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
</script>

<template>
    <div class="form-help form-text" v-html="formattedContent" />
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.form-help {
    &:deep(h3) {
        font-size: $h4-font-size;
        font-weight: bold;
    }

    &:deep(h4) {
        font-size: $h5-font-size;
        font-weight: bold;
    }

    &:deep(h5) {
        font-size: $h6-font-size;
        font-weight: bold;
    }

    &:deep(h6) {
        font-size: $h6-font-size;
        text-decoration: underline;
    }
}
</style>
