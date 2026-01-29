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
    <q-toolbar class="bg-primary glossy text-white">
        <q-toolbar-title>
            <q-avatar rounded>
                <router-link to="/">
                    <img alt="Tool Shed Logo" src="/static/favicon.ico" />
                </router-link>
            </q-avatar>
            <!-- <q-btn flat round dense icon="menu" class="q-mr-sm" /> -->
            <span class="text-bold">
                {{ title }}
            </span>
        </q-toolbar-title>
        <q-btn-dropdown stretch flat label="Explore">
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
        <q-btn-dropdown stretch flat :label="authStore.user.username" v-if="authStore.user">
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
        <q-btn-dropdown stretch flat label="Admin" v-if="admin">
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
            v-if="authStore.user"
        />
        <q-btn class="q-mx-sm toolbar-login" flat round dense icon="login" to="/login" title="Login" v-else />
        <q-btn class="q-mx-sm toolbar-help" flat round dense icon="help" to="/help" title="Help" />
    </q-toolbar>
</template>
