<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { watch } from "vue";

import { isRegisteredUser } from "@/api";
import { useUserStore } from "@/stores/userStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ServiceCredentialsGroupsList from "@/components/User/Credentials/ServiceCredentialsGroupsList.vue";

const breadcrumbItems = [{ title: "User Preferences", to: "/user" }, { title: "Tools Credentials Management" }];

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
const { isBusy, busyMessage, userToolsGroups } = storeToRefs(userToolsServiceCredentialsStore);

watch(
    () => currentUser.value,
    async () => {
        if (isRegisteredUser(currentUser.value)) {
            await userToolsServiceCredentialsStore.fetchAllUserToolsServiceCredentials();
        }
    },
    { immediate: true }
);
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <div class="mb-2">You can manage your provided credentials for tools here.</div>

        <BAlert v-if="isBusy" show>
            <LoadingSpan :message="busyMessage" />
        </BAlert>
        <BAlert v-else-if="!isBusy && !userToolsGroups.length" variant="info" show>
            No credentials have been defined for any tools or services yet.
        </BAlert>
        <div v-else-if="!isBusy">
            <ServiceCredentialsGroupsList :service-groups="userToolsGroups" />
        </div>
    </div>
</template>
