<script setup>
import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";
import MastheadItem from "./MastheadItem";
import { loadWebhookMenuItems } from "./_webhooks";
import QuotaMeter from "./QuotaMeter";
import { safePath } from "utils/redirect";
import { getActiveTab } from "./utilities";
import { watch, ref } from "vue";
import { onMounted } from "vue";
import { useRoute } from "vue-router/composables";
import ThemeSelector from "./ThemeSelector.vue";

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

function setActiveTab() {
    const currentRoute = route.path;
    activeTab.value = getActiveTab(currentRoute, props.tabs) || activeTab.value;
}

function onWindowToggle() {
    windowToggle.value = !windowToggle.value;
}

watch(
    () => route.path,
    () => {
        setActiveTab();
    }
);

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
                :href="safePath(logoUrl)">
                <img alt="logo" :src="safePath(logoSrc)" />
                <img v-if="logoSrcSecondary" alt="logo" :src="safePath(logoSrcSecondary)" />
            </b-navbar-brand>
            <b-nav-item v-if="brand" class="navbar-brand-title" disabled>
                {{ brand }}
            </b-nav-item>
        </b-navbar-nav>
        <b-navbar-nav>
            <masthead-item
                v-for="(tab, idx) in props.tabs"
                v-show="tab.hidden !== true"
                :key="`tab-${idx}`"
                :tab="tab"
                :active-tab="activeTab"
                @open-url="emit('open-url', $event)" />
            <ThemeSelector />
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
    .navbar-brand-title {
        font-weight: bold;
        font-family: Verdana, sans-serif;
        font-size: calc($masthead-height / 3);
        line-height: calc($masthead-height / 3);
        color: var(--masthead-text-color);
    }
}
</style>
