<script setup>
import { BNavItem, VBPopoverPlugin, VBTooltipPlugin } from "bootstrap-vue";
import { withPrefix } from "utils/redirect";
import Vue, { computed, getCurrentInstance } from "vue";

Vue.use(VBPopoverPlugin);
Vue.use(VBTooltipPlugin);

const instance = getCurrentInstance().proxy;
const emit = defineEmits(["click", "open-url"]);

/* props */
const props = defineProps({
    tab: {
        type: Object,
        default: null,
    },
    id: {
        type: String,
    },
    toggle: {
        type: Boolean,
        default: false,
    },
    activeTab: {
        type: String,
        default: null,
    },
});

/* computed */
const popoverNote = computed(
    () => `Please <a href="${withPrefix("/login")}">log in or register</a> to use this feature.`
);
const linkClasses = computed(() => ({
    "nav-icon": props.tab.icon,
    toggle: props.toggle,
}));
const iconClasses = computed(() =>
    Object.fromEntries([
        ["fa fa-fw", true],
        [props.tab.icon, !!props.tab.icon],
    ])
);

/* methods */
function open(tab, event) {
    if (tab.onclick) {
        event.preventDefault();
        tab.onclick();
        emit("click");
    } else if (tab.disabled) {
        event.preventDefault();
        instance.$root.$emit("bv::hide::tooltip");
        instance.$root.$emit("bv::show::popover", id);
        setTimeout(() => {
            instance.$root.$emit("bv::hide::popover", id);
        }, 3000);
    } else if (!tab.menu) {
        event.preventDefault();
        emit("open-url", { ...tab });
    }
}
</script>

<template>
    <BNavItem
        :id="id"
        v-b-tooltip.hover.bottom
        v-b-popover.manual.bottom="{ id: id, content: popoverNote, html: true }"
        :href="withPrefix(tab.url)"
        :target="tab.target || '_parent'"
        :link-classes="linkClasses"
        :title="tab.tooltip"
        @click="open(tab, $event)">
        <template v-if="tab.icon">
            <!-- If this is an icon-based tab, inject tooltip directly for screen readers -->
            <span class="sr-only">{{ tab.tooltip || id }}</span>
            <span :class="iconClasses" />
            <span v-if="toggle" class="nav-note fa fa-check" />
        </template>
        <template v-else>
            {{ tab.title }}
        </template>
    </BNavItem>
</template>
