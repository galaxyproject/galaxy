<script setup>
import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";
import MastheadItem from "./MastheadItem";
import { loadWebhookMenuItems } from "./_webhooks";
import QuotaMeter from "./QuotaMeter";
import { withPrefix } from "utils/redirect";
import { getActiveTab } from "./utilities";
import { watch, ref, reactive } from "vue";
import { onMounted, onBeforeMount } from "vue";
import { useRoute } from "vue-router/composables";
import { useEntryPointStore } from "stores/entryPointStore";

const route = useRoute();
const emit = defineEmits(["open-url"]);

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

const activeTab = ref(props.initialActiveTab);
const extensionTabs = ref([]);
const windowToggle = ref(false);

let entryPointStore;
const itsMenu = reactive({
    id: "interactive",
    url: "/interactivetool_entry_points/list",
    tooltip: "See Running Interactive Tools",
    icon: "fa-cogs",
    hidden: true,
});

function setActiveTab() {
    const currentRoute = route.path;
    activeTab.value = getActiveTab(currentRoute, props.tabs) || activeTab.value;
}

function onWindowToggle() {
    windowToggle.value = !windowToggle.value;
}
function updateVisibility(isActive) {
    itsMenu.hidden = !isActive;
}

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
            <b-navbar-brand
                v-b-tooltip.hover
                class="ml-2 mr-1"
                title="Home"
                aria-label="homepage"
                :href="withPrefix(logoUrl)">
                <img alt="logo" :src="withPrefix(logoSrc)" />
                <img v-if="logoSrcSecondary" alt="logo" :src="withPrefix(logoSrcSecondary)" />
            </b-navbar-brand>
            <span v-if="brand" class="navbar-text">
                {{ brand }}
            </span>
        </b-navbar-nav>
        <b-navbar-nav>
            <masthead-item
                v-for="(tab, idx) in props.tabs"
                v-show="tab.hidden !== true"
                :key="`tab-${idx}`"
                :tab="tab"
                :active-tab="activeTab"
                @open-url="emit('open-url', $event)" />
            <masthead-item
                v-show="itsMenu.hidden !== true"
                :key="`its-tab`"
                :tab="itsMenu"
                :active-tab="activeTab"
                @open-url="emit('open-url', $event)" />
            <masthead-item
                v-for="(tab, idx) in extensionTabs"
                v-show="tab.hidden !== true"
                :key="`extension-tab-${idx}`"
                :tab="tab"
                :active-tab="activeTab"
                @open-url="emit('open-url', $event)" />
            <masthead-item v-if="windowTab" :tab="windowTab" :toggle="windowToggle" @click="onWindowToggle" />
        </b-navbar-nav>
        <quota-meter />
    </b-navbar>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

#masthead {
    padding: 0;
    margin-bottom: 0;
    background: var(--masthead-color);
    height: $masthead-height;
    &:deep(.navbar-nav) {
        height: $masthead-height;
        & > li {
            // This allows the background color to fill the full height of the
            // masthead, while still keeping the contents centered (using flex)
            min-height: 100%;
            display: flex;
            align-items: center;
            background: var(--masthead-link-color);
            &:hover {
                background: var(--masthead-link-hover);
            }
            &.show,
            &.active {
                background: var(--masthead-link-active);
                .nav-link {
                    color: var(--masthead-text-active);
                }
            }
            .nav-link {
                position: relative;
                cursor: pointer;
                text-decoration: none;
                color: var(--masthead-text-color);
                &:hover {
                    color: var(--masthead-text-hover);
                }
                &.nav-icon {
                    font-size: 1.3em;
                    .nav-note {
                        position: absolute;
                        left: 1.9rem;
                        top: 1.9rem;
                        font-size: 0.6rem;
                        font-weight: bold;
                    }
                }
                &.toggle {
                    color: var(--masthead-text-hover);
                }
            }
        }
    }
    .navbar-brand {
        cursor: pointer;
        img {
            display: inline;
            border: none;
            height: 2.3rem;
        }
    }
    .navbar-text {
        font-weight: bold;
        font-family: Verdana, sans-serif;
        font-size: 1rem;
        line-height: 2rem;
        color: var(--masthead-text-color);
    }
}
</style>
