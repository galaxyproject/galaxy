<script setup lang="ts">
import { faCircleQuestion, faRightFromBracket, faRightToBracket } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { GButton, GDropdown, GDropdownGroup, GDropdownItem } from "@galaxyproject/galaxy-ui"
import { computed } from "vue"
import { useAuthStore } from "@/stores"

defineProps({
    title: {
        type: String,
        required: true,
    },
})

const authStore = useAuthStore()
void authStore.setup()

const admin = computed(() => authStore.user && authStore.user.is_admin)
</script>
<template>
    <nav class="shed-masthead" aria-label="Main navigation">
        <div class="masthead-title">
            <router-link to="/" aria-label="Tool Shed Home" class="masthead-brand">
                <img alt="Galaxy" src="../assets/galaxy_logo.svg" />
            </router-link>
            <span class="masthead-name">
                {{ title }}
            </span>
        </div>
        <GDropdown text="Explore" right toggle-class="masthead-toggle" menu-class="masthead-menu">
            <GDropdownGroup header="Repositories">
                <GDropdownItem to="/repositories_by_category">
                    <span class="menu-label">Categories</span>
                    <span class="menu-caption">Browse repositories by category</span>
                </GDropdownItem>
                <GDropdownItem to="/repositories_by_owner">
                    <span class="menu-label">Owners</span>
                    <span class="menu-caption">Browse repositories by owner</span>
                </GDropdownItem>
                <GDropdownItem to="/repositories_by_search">
                    <span class="menu-label">Search</span>
                    <span class="menu-caption">Search for repositories</span>
                </GDropdownItem>
            </GDropdownGroup>
        </GDropdown>
        <GDropdown
            v-if="authStore.user"
            :text="authStore.user.username"
            right
            toggle-class="masthead-toggle"
            menu-class="masthead-menu"
        >
            <GDropdownItem to="/user/api_key">
                <span class="menu-label">API Key</span>
                <span class="menu-caption">Manage API key (needed for Planemo)</span>
            </GDropdownItem>
            <GDropdownItem to="/user/change_password">
                <span class="menu-label">Change Password</span>
                <span class="menu-caption">Change your password</span>
            </GDropdownItem>
        </GDropdown>
        <GDropdown v-if="admin" text="Admin" right toggle-class="masthead-toggle" menu-class="masthead-menu">
            <GDropdownGroup header="Admin Tools">
                <GDropdownItem to="/admin">
                    <span class="menu-label">Control Panel</span>
                    <span class="menu-caption">Admin management console (currently just for search statistics)</span>
                </GDropdownItem>
            </GDropdownGroup>
            <GDropdownGroup header="Dev Tools">
                <GDropdownItem to="/_component_showcase">
                    <span class="menu-label">Component Showcase</span>
                    <span class="menu-caption">Demonstrate common components used to build app to assist design</span>
                </GDropdownItem>
            </GDropdownGroup>
        </GDropdown>
        <GButton
            v-if="authStore.user"
            class="masthead-icon toolbar-logout"
            icon-only
            transparent
            title="Logout"
            aria-label="Logout"
            @click="authStore.logout()"
        >
            <FontAwesomeIcon :icon="faRightFromBracket" />
        </GButton>
        <GButton
            v-else
            class="masthead-icon toolbar-login"
            icon-only
            transparent
            to="/login"
            title="Login"
            aria-label="Login"
        >
            <FontAwesomeIcon :icon="faRightToBracket" />
        </GButton>
        <GButton class="masthead-icon toolbar-help" icon-only transparent to="/help" title="Help" aria-label="Help">
            <FontAwesomeIcon :icon="faCircleQuestion" />
        </GButton>
    </nav>
</template>
<style lang="scss" scoped>
// Galaxy masthead idiom: flat dark bar, gold hover/active accents.
.shed-masthead {
    display: flex;
    align-items: center;
    min-height: 50px;
    padding: 0 var(--spacing-3);
    color: white;
    background: var(--color-galaxy-dark, #2c3143);

    // Masthead controls read as light text on the dark bar, turning gold on hover and while open
    // .g-button keeps GButton's own variant colors from outranking the bar's
    :deep(.masthead-toggle),
    :deep(.g-button.masthead-icon) {
        color: white;
        background: none;
        border: none;
        // Full masthead height, so the whole strip is the hit area as with Quasar's stretched buttons
        height: 50px;
        padding: 0 var(--spacing-3);
        font-weight: bold;

        &:hover,
        &[aria-expanded="true"] {
            color: var(--color-galaxy-gold, #ffd700);
        }
    }

    :deep(.masthead-icon) svg {
        font-size: 1.25rem;
    }

    :deep(.masthead-menu) {
        box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.15);
        font-weight: normal;
    }

    :deep(.masthead-menu .dropdown-item) {
        white-space: normal;
        min-width: 16rem;
    }

    .menu-label {
        display: block;
    }

    .menu-caption {
        display: block;
        font-size: var(--font-size-small);
        color: var(--color-grey-600);
    }

    .masthead-brand {
        display: inline-block;
        vertical-align: middle;
        // The logo is a wordmark, so the title follows it as the next word
        margin-right: 0.4rem;

        img {
            display: block;
            height: 1.75rem;
        }
    }

    .masthead-title {
        flex: 1;
        display: flex;
        align-items: center;
        min-width: 0;
        font-size: 1.3rem;
    }

    .masthead-name {
        font-weight: bold;

        // Phones get the logo alone, which already reads "Galaxy"
        @media (max-width: 599px) {
            display: none;
        }
    }
}
</style>
