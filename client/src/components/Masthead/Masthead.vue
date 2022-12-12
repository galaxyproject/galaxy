<script setup>
import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";
import MastheadItem from "./MastheadItem";
import { loadWebhookMenuItems } from "./_webhooks";
import QuotaMeter from "./QuotaMeter";
import { safePath } from "utils/redirect";
import { getActiveTab } from "./utilities";
import { watch, computed, ref, reactive } from "vue";
import { onMounted, onBeforeMount } from "vue";
import { useRoute } from "vue-router/composables";
import { useEntryPointStore } from "../../stores/entryPointStore";
// basics
const route = useRoute();
const emit = defineEmits(["open-url"]);

/* props */
const props = defineProps({
    tabs: {
        type: Array,
        default: () => [],
    },
    brand: {
        type: String,
        default: null,
    },
    initialActiveTab: {
        type: String,
        default: "analysis",
    },
    logoUrl: {
        type: String,
        default: null,
    },
    logoSrc: {
        type: String,
        default: null,
    },
    logoSrcSecondary: {
        type: String,
        default: null,
    },
    windowTab: {
        type: Object,
        default: null,
    },
});

/* refs */
const activeTab = ref(props.initialActiveTab);
const extensionTabs = ref([]);
const windowToggle = ref(false);

let entryPointStore;
const its_menu = reactive({
    id: "interactive",
    url: "/interactivetool_entry_points/list",
    tooltip: "See Running Interactive Tools",
    icon: "fa-cogs",
    hidden: true,
});

/* computed */
const allTabs = computed(() => {
    return [].concat(props.tabs, its_menu, extensionTabs.value);
});

/* methods */
function setActiveTab() {
    const currentRoute = route.path;
    activeTab.value = getActiveTab(currentRoute, props.tabs) || activeTab.value;
}
function onWindowToggle() {
    windowToggle.value = !windowToggle.value;
}
function updateVisibility(isActive) {
    its_menu.hidden = !isActive;
}

/* watchers */
watch(
    () => route.path,
    () => {
        setActiveTab();
    }
);

/* lifecyle */
onBeforeMount(() => {
    entryPointStore = useEntryPointStore();
    entryPointStore.ensurePollingEntryPoints();
    entryPointStore.$subscribe((mutation, state) => {
        updateVisibility(state.entryPoints.length > 0);
    });
});
onMounted(() => {
    loadWebhookMenuItems(extensionTabs.value);
    setActiveTab();
});
</script>

<template>
    <b-navbar id="masthead" type="dark" role="navigation" aria-label="Main" class="justify-content-between">
        <b-navbar-nav>
            <b-navbar-brand id="analysis" :href="safePath(logoUrl)" aria-label="homepage">
                <b-button v-b-tooltip.hover variant="link" size="sm" title="Home">
                    <img alt="logo" :src="safePath(logoSrc)" />
                    <img v-if="logoSrcSecondary" alt="logo" :src="safePath(logoSrcSecondary)" />
                </b-button>
            </b-navbar-brand>
            <b-nav-item v-if="brand" class="navbar-brand-title" disabled>
                {{ brand }}
            </b-nav-item>
        </b-navbar-nav>
        <b-navbar-nav>
            <masthead-item
                v-for="(tab, idx) in allTabs"
                v-show="tab.hidden !== true"
                :key="`tab-${idx}`"
                :tab="tab"
                :active-tab="activeTab"
                @open-url="emit('open-url', $event)" />
            <masthead-item v-if="windowTab" :tab="windowTab" :toggle="windowToggle" @click="onWindowToggle" />
        </b-navbar-nav>
        <quota-meter />
    </b-navbar>
</template>
