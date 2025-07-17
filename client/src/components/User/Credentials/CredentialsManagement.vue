<script setup lang="ts">
import { storeToRefs } from "pinia";
import { ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { UserCredentials } from "@/api/users";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import GCard from "@/components/Common/GCard.vue";

const breadcrumbItems = [{ title: "User Preferences", to: "/user" }, { title: "Credentials Management" }];

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const loading = ref(false);
const error = ref(null);
const credentialsList = ref<UserCredentials[]>([]);
const selectedCredential = ref<UserCredentials[]>([]);

async function fetchCredentials() {
    const { data, error } = await GalaxyApi().GET("/api/users/{user_id}/credentials", {
        params: {
            path: {
                user_id: currentUser.value?.id,
            },
        },
    });

    if (error) {
        Toast.error(error.err_msg, "Error fetching credentials");
        return [];
    }

    credentialsList.value = data;
}

watch(
    () => currentUser.value,
    async () => {
        if (!currentUser.value?.isAnonymous && currentUser.value?.id) {
            await fetchCredentials();
        }
    },
    { immediate: true }
);
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <span> You can manage your provided for tools and services here. </span>

        <GCard v-for="credential in credentialsList" :key="credential.id" :title="credential.name" />
    </div>
</template>
