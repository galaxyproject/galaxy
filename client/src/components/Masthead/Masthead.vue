<script setup>
import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { userLogout } from "utils/logout";
import { withPrefix } from "utils/redirect";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";

import { loadWebhookMenuItems } from "./_webhooks";
import MastheadDropdown from "./MastheadDropdown";
import MastheadItem from "./MastheadItem";
import QuotaMeter from "./QuotaMeter";

const { isAnonymous, currentUser } = storeToRefs(useUserStore());

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

const extensionTabs = ref([]);
const windowToggle = ref(false);

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

onMounted(() => {
    loadWebhookMenuItems(extensionTabs.value);
});
</script>

<template>
    <BNavbar id="masthead" type="dark" role="navigation" aria-label="Main" class="justify-content-between">
        <BNavbarNav>
            <BNavbarBrand
                id="analysis"
                v-b-tooltip.hover
                class="ml-2 mr-2 p-0"
                title="Home"
                aria-label="homepage"
                :href="withPrefix(logoUrl)">
                <img alt="logo" :src="withPrefix(logoSrc)" />
                <img v-if="logoSrcSecondary" alt="logo" :src="withPrefix(logoSrcSecondary)" />
            </BNavbarBrand>
            <span v-if="brand" class="navbar-text py-0 px-2">
                {{ brand }}
            </span>
        </BNavbarNav>
        <BNavbarNav v-if="isConfigLoaded" class="mr-1">
            <MastheadItem
                v-if="windowTab"
                :id="windowTab.id"
                :icon="windowTab.icon"
                :toggle="windowToggle"
                :tooltip="windowTab.tooltip"
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
                @click="tab.onclick ? tab.onclick : undefined" />
            <MastheadItem
                id="help"
                icon="fa-question"
                url="/about"
                tooltip="Support, Contact, and Community"
                @click="openUrl('/about')" />
            <QuotaMeter />
            <MastheadItem
                v-if="isAnonymous && config.allow_user_creation"
                id="user"
                class="loggedout-only"
                title="Login or Register"
                @click="openUrl('/login/start')" />
            <MastheadItem
                v-if="isAnonymous && !config.allow_user_creation"
                id="user"
                class="loggedout-only"
                title="Login"
                @click="openUrl('/login/start')" />
            <MastheadDropdown
                v-if="currentUser && !isAnonymous && !config.single_user"
                id="user"
                class="loggedin-only"
                icon="fa-user"
                :title="currentUser.username"
                tooltip="User Preferences"
                :menu="[
                    {
                        title: 'Preferences',
                        icon: 'fa-gear',
                        handler: () => openUrl('/user'),
                    },
                    {
                        title: 'Sign Out',
                        icon: 'fa-sign-out-alt',
                        handler: () => userLogout(),
                    },
                ]"
                @click="userLogout" />
        </BNavbarNav>
        <Icon v-else icon="spinner" class="fa-spin mr-2 text-light" />
    </BNavbar>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

#masthead {
    padding: 0;
    margin-bottom: 0;
    background: var(--masthead-color);
    height: var(--masthead-height);
    &:deep(.navbar-nav) {
        height: var(--masthead-height);
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
                margin-left: 0.25rem;
                &:hover {
                    color: var(--masthead-text-hover);
                }
                &.nav-icon {
                    font-size: 1.2em;
                    .nav-note {
                        position: absolute;
                        left: 1.6rem;
                        top: 1.6rem;
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
        line-height: var(--masthead-height);
        img {
            filter: $text-shadow;
            display: inline;
            border: none;
            height: var(--masthead-logo-height);
            padding: inherit;
        }
    }
    .navbar-text {
        filter: $text-shadow;
        font-weight: bold;
        font-family: Verdana, sans-serif;
        font-size: 1rem;
        line-height: var(--masthead-height);
        color: var(--masthead-text-color);
    }
}
</style>
