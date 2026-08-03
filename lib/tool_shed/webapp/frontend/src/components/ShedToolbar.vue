<script setup lang="ts">
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
    <q-toolbar class="shed-masthead text-white" role="navigation" aria-label="Main navigation">
        <q-toolbar-title>
            <router-link to="/" aria-label="Tool Shed Home" class="masthead-brand">
                <img alt="Galaxy" src="../assets/galaxy_logo.svg" />
            </router-link>
            <!-- Phones get the logo alone, which already reads "Galaxy" -->
            <span class="text-bold gt-xs">
                {{ title }}
            </span>
        </q-toolbar-title>
        <q-btn-dropdown stretch flat label="Explore" aria-haspopup="menu">
            <q-list>
                <q-item-label header>Repositories</q-item-label>
                <q-item clickable v-close-popup tabindex="0" to="/repositories_by_category">
                    <q-item-section>
                        <q-item-label>Categories</q-item-label>
                        <q-item-label caption>Browse repositories by category</q-item-label>
                    </q-item-section>
                </q-item>
                <q-item clickable v-close-popup tabindex="0" to="/repositories_by_owner">
                    <q-item-section>
                        <q-item-label>Owners</q-item-label>
                        <q-item-label caption>Browse repositories by owner</q-item-label>
                    </q-item-section>
                </q-item>
                <q-item clickable v-close-popup tabindex="0" to="/repositories_by_search">
                    <q-item-section>
                        <q-item-label>Search</q-item-label>
                        <q-item-label caption>Search for repositories</q-item-label>
                    </q-item-section>
                </q-item>
                <!--
                    In the future would love to have tool centric exploration
                <q-separator inset spaced />
                <q-item-label header>Tools</q-item-label>
                -->
            </q-list>
        </q-btn-dropdown>
        <q-btn-dropdown stretch flat :label="authStore.user.username" aria-haspopup="menu" v-if="authStore.user">
            <q-list>
                <q-item clickable v-close-popup tabindex="0" to="/user/api_key">
                    <q-item-section>
                        <q-item-label>API Key</q-item-label>
                        <q-item-label caption>Manage API key (needed for Planemo)</q-item-label>
                    </q-item-section>
                </q-item>
                <q-item clickable v-close-popup tabindex="0" to="/user/change_password">
                    <q-item-section>
                        <q-item-label>Change Password</q-item-label>
                        <q-item-label caption>Change your password</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
        </q-btn-dropdown>
        <q-btn-dropdown stretch flat label="Admin" aria-haspopup="menu" v-if="admin">
            <q-list>
                <q-item-label header>Admin Tools</q-item-label>
                <q-item clickable v-close-popup tabindex="0" to="/admin">
                    <q-item-section>
                        <q-item-label>Control Panel</q-item-label>
                        <q-item-label caption
                            >Admin management console (currently just for search statistics)</q-item-label
                        >
                    </q-item-section>
                </q-item>
                <q-item-label header>Dev Tools</q-item-label>
                <q-item clickable v-close-popup tabindex="0" to="/_component_showcase">
                    <q-item-section>
                        <q-item-label>Component Showcase</q-item-label>
                        <q-item-label caption
                            >Demonstrate common components used to build app to assist design</q-item-label
                        >
                    </q-item-section>
                </q-item>
            </q-list>
        </q-btn-dropdown>
        <q-btn
            class="q-mx-sm toolbar-logout"
            flat
            round
            dense
            icon="logout"
            @click="authStore.logout()"
            title="Logout"
            aria-label="Logout"
            v-if="authStore.user"
        />
        <q-btn
            class="q-mx-sm toolbar-login"
            flat
            round
            dense
            icon="login"
            to="/login"
            title="Login"
            aria-label="Login"
            v-else
        />
        <q-btn class="q-mx-sm toolbar-help" flat round dense icon="help" to="/help" title="Help" aria-label="Help" />
    </q-toolbar>
</template>
<style lang="scss" scoped>
// Galaxy masthead idiom: flat dark bar, gold hover/active accents.
.shed-masthead {
    background: var(--color-galaxy-dark, #2c3143);

    :deep(.q-btn:hover),
    :deep(.q-btn[aria-expanded="true"]) {
        color: var(--color-galaxy-gold, #ffd700);
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

    .q-toolbar__title {
        display: flex;
        align-items: center;
    }
}
</style>
