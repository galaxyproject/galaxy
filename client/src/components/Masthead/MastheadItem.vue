<script setup>
import Vue from "vue";
import { VBPopoverPlugin, VBTooltipPlugin } from "bootstrap-vue";
import { BNavItem, BNavItemDropdown, BDropdownItem } from "bootstrap-vue";
import { withPrefix } from "utils/redirect";
import { ref, computed } from "vue";
import { getCurrentInstance } from "vue";

Vue.use(VBPopoverPlugin);
Vue.use(VBTooltipPlugin);

const instance = getCurrentInstance().proxy;
const emit = defineEmits(["click", "open-url"]);
const dropdown = ref(null);

/* props */
const props = defineProps({
    tab: {
        type: Object,
        default: null,
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
const menu = computed(() => props.tab.menu);
const popoverNote = computed(
    () => `Please <a href="${withPrefix("/login")}">log in or register</a> to use this feature.`
);
const classes = computed(() => {
    const isActiveTab = props.tab.id == props.activeTab;
    return Object.fromEntries([
        ["active", isActiveTab],
        [props.tab.cls, !!props.tab.cls],
    ]);
});
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
        instance.$root.$emit("bv::show::popover", tab.id);
        setTimeout(() => {
            instance.$root.$emit("bv::hide::popover", tab.id);
        }, 3000);
    } else if (!tab.menu) {
        event.preventDefault();
        emit("open-url", { ...tab });
    }
}
</script>

<template>
    <b-nav-item
        v-if="!menu"
        :id="tab.id"
        v-b-tooltip.hover.bottom
        v-b-popover.manual.bottom="{ id: tab.id, content: popoverNote, html: true }"
        :class="classes"
        :href="withPrefix(tab.url)"
        :target="tab.target || '_parent'"
        :link-classes="linkClasses"
        :title="tab.tooltip"
        @click="open(tab, $event)">
        <template v-if="tab.icon">
            <!-- If this is an icon-based tab, inject tooltip directly for screen readers -->
            <span class="sr-only">{{ tab.tooltip || tab.id }}</span>
            <span :class="iconClasses" />
            <span v-if="toggle" class="nav-note fa fa-check" />
        </template>
        <template v-else>
            {{ tab.title }}
        </template>
    </b-nav-item>
    <b-nav-item-dropdown
        v-else
        :id="tab.id"
        ref="dropdown"
        v-b-tooltip.hover.bottom
        v-b-popover.manual.bottom="{ id: tab.id, content: popoverNote, html: true }"
        :class="classes"
        :text="tab.title"
        href="#"
        :title="tab.tooltip"
        @show="open(tab, $event)">
        <template v-if="tab.icon" v-slot:button-content>
            <span class="sr-only">{{ tab.tooltip || tab.id }}</span>
            <span :class="iconClasses" />
        </template>
        <template v-for="(item, idx) in tab.menu">
            <div v-if="item.divider" :key="`divider-${idx}`" class="dropdown-divider" />
            <b-dropdown-item
                v-else-if="item.hidden !== true"
                :key="`item-${idx}`"
                :href="withPrefix(item.url)"
                :target="item.target || '_parent'"
                role="menuitem"
                :active="item.disabled"
                :disabled="item.disabled"
                @click="open(item, $event)">
                {{ item.title }}
            </b-dropdown-item>
        </template>
    </b-nav-item-dropdown>
</template>
