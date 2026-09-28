<template>
    <div class="code-row">
        <div class="code-row-label">
            <span v-if="helpUri">
                <HelpText :uri="helpUri" :text="codeLabel" />
            </span>
            <span v-else>
                {{ codeLabel }}
            </span>
        </div>
        <div v-if="codeItem" class="code-row-body">
            <pre ref="pre" :class="codeClass">{{ codeItem }}</pre>
            <button
                v-if="needsToggle"
                type="button"
                class="code-row-toggle"
                :title="`click to ${action}`"
                @click="toggleExpanded">
                <FontAwesomeIcon :icon="iconClass" fixed-width />
            </button>
        </div>
        <i v-else class="code-row-empty">empty</i>
    </div>
</template>
<script>
import { faCompressAlt, faExpandAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import HelpText from "@/components/Help/HelpText.vue";

export default {
    components: {
        FontAwesomeIcon,
        HelpText,
    },
    props: {
        codeLabel: String,
        codeItem: String,
        helpUri: String,
    },
    data() {
        return {
            expanded: false,
            lastPos: 0,
            needsToggle: false,
            faCompressAlt,
            faExpandAlt,
        };
    },
    computed: {
        action() {
            return this.expanded ? "collapse" : "expand";
        },
        codeClass() {
            return this.expanded ? "code" : "code preview";
        },
        iconClass() {
            return this.expanded ? this.faCompressAlt : this.faExpandAlt;
        },
    },
    updated() {
        try {
            var codeDiv = this.$el.querySelector(".code");
            if (codeDiv.scrollTop + codeDiv.offsetHeight >= this.lastPos - 5) {
                // scroll is at the bottom
                codeDiv.scrollTop = codeDiv.scrollHeight;
            }
            this.lastPos = codeDiv.scrollHeight;
        } catch (exception) {
            console.debug("Code div is not present");
        }
        this.checkNeedsToggle();
        this.observePre();
    },
    mounted() {
        this.checkNeedsToggle();
        this.resizeObserver = new ResizeObserver(() => this.checkNeedsToggle());
        this.observePre();
    },
    beforeUnmount() {
        this.resizeObserver?.disconnect();
    },
    methods: {
        toggleExpanded() {
            if (this.codeItem) {
                this.expanded = !this.expanded;
            }
        },
        checkNeedsToggle() {
            // Only the collapsed (single-line, ellipsized) box can be reliably measured for
            // overflow — once expanded it wraps/scrolls, so skip re-checking in that state.
            if (this.expanded) {
                return;
            }
            const pre = this.$refs.pre;
            this.needsToggle = !!pre && pre.scrollWidth > pre.clientWidth;
        },
        observePre() {
            // .observe() on an already-observed element is a no-op, so it's safe to call this
            // on every update — it just picks up the <pre> once codeItem first becomes truthy.
            if (this.$refs.pre) {
                this.resizeObserver?.observe(this.$refs.pre);
            }
        },
    },
};
</script>

<style scoped lang="scss">
.code-row {
    margin-bottom: 1rem;

    &:last-child {
        margin-bottom: 0;
    }
}

.code-row-label {
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--color-grey-500);
    margin-bottom: 0.35rem;
}

.code-row-body {
    display: flex;
    align-items: flex-start;
    background: var(--color-blue-700);
    border-radius: 0.375rem;
    overflow: hidden;

    .code {
        word-wrap: break-word;
    }
}

.code-row-toggle {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    margin-right: 0.5rem;
    margin-top: 0.25rem;
    border: none;
    background: transparent;
    color: var(--color-grey-100);
    transition: background-color 0.15s ease;

    &:hover,
    &:focus-visible {
        background-color: var(--color-grey-600);
    }
}

.code-row-empty {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.65rem 0.85rem;
    background: var(--color-grey-100);
    border: 1px dashed var(--color-grey-300);
    border-radius: 0.375rem;
    color: var(--color-grey-400);
    font-size: 0.85rem;
}

.code {
    max-height: 50em;
    overflow: auto;
}

pre {
    flex: 1;
    min-width: 0;
    margin: 0;
    background: transparent;
    border: none;
}
</style>
