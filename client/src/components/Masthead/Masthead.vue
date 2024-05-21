<script setup>
import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { userLogout } from "utils/logout";
import { withPrefix } from "utils/redirect";
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";

import { loadWebhookMenuItems } from "./_webhooks";
import MastheadItem from "./MastheadItem";
import QuotaMeter from "./QuotaMeter";
import { getActiveTab } from "./utilities";

const { isAnonymous } = storeToRefs(useUserStore());

const route = useRoute();
const router = useRouter();
const { config, isConfigLoaded } = useConfig();

const props = defineProps({
    brand: {
        type: String,
        default: null,
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

function openUrl(url, target = null) {
    if (!target) {
        router.push(url);
    } else {
        url = withPrefix(url);
        if (target == "_blank") {
            window.open(url);
        } else {
            window.location = url;
        }
    }
}

function onWindowToggle() {
    windowToggle.value = !windowToggle.value;
    props.windowTab.onclick();
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
    <BNavbar
        v-if="isConfigLoaded"
        id="masthead"
        type="dark"
        role="navigation"
        aria-label="Main"
        class="justify-content-between">
        <BNavbarNav>
            <BNavbarBrand
                v-b-tooltip.hover
                class="ml-2 mr-2 p-0"
                title="Home"
                aria-label="homepage"
                :href="withPrefix(logoUrl)">
                <img alt="logo" :src="withPrefix(logoSrc)" />
                <img v-if="logoSrcSecondary" alt="logo" :src="withPrefix(logoSrcSecondary)" />
            </BNavbarBrand>
            <span v-if="brand" class="navbar-text px-2">
                {{ brand }}
            </span>
        </BNavbarNav>
        <BNavbarNav>
            <MastheadItem id="analysis" title="Tools and Current History" icon="fa-home" @click="openUrl('/')" />
            <MastheadItem
                v-if="windowTab"
                :id="windowTab.id"
                :title="windowTab.title"
                :icon="windowTab.icon"
                :toggle="windowToggle"
                @click="onWindowToggle" />
            <MastheadItem
                v-for="(tab, idx) in extensionTabs"
                v-show="tab.hidden !== true"
                :id="tab.id"
                :key="`extension-tab-${idx}`"
                :title="tab.title"
                :icon="tab.icon"
                :url="tab.url"
                :tooltip="tab.tooltip"
                :target="tab.target"
                @click="tab.onclick" />
            <MastheadItem
                id="help"
                title="Support, contact, and community"
                icon="fa-question"
                @click="openUrl('/about')" />
            <QuotaMeter />
            <MastheadItem
                v-if="isAnonymous && config.allow_user_creation"
                id="user"
                title="Log in or Register"
                @click="openUrl('/login/start')" />
            <MastheadItem
                v-if="isAnonymous && !config.allow_user_creation"
                id="user"
                title="Login"
                @click="openUrl('/login/start')" />
            <MastheadItem
                v-if="!isAnonymous && !config.single_user"
                id="user"
                title="Logout"
                icon="fa-sign-out-alt"
                @click="userLogout" />
        </BNavbarNav>
    </BNavbar>
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
                margin-right: 0.25rem;
                &:hover {
                    color: var(--masthead-text-hover);
                }
                &.nav-icon {
                    font-size: 1.2em;
                    .nav-note {
                        position: absolute;
                        left: 1.6rem;
                        top: 1.6rem;
                        font-size: 0.4rem;
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
        line-height: $masthead-height;
        img {
            filter: $text-shadow;
            display: inline;
            border: none;
            height: 2rem;
        }
    }
    .navbar-text {
        filter: $text-shadow;
        font-weight: bold;
        font-family: Verdana, sans-serif;
        font-size: 1rem;
        line-height: $masthead-height;
        color: var(--masthead-text-color);
    }
}
</style>
