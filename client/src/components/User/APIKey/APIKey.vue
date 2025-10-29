<script setup>
import { faPlus, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { getGalaxyInstance } from "@/app";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

import APIKeyItem from "./APIKeyItem.vue";
import svc from "./model/service";

const apiKey = ref(null);
const loading = ref(false);
const errorMessage = ref(null);
const createLoading = ref(false);

const currentUserId = getGalaxyInstance().user.id;

const getAPIKey = () => {
    loading.value = true;
    svc.getAPIKey(currentUserId)
        .then((result) => (apiKey.value = result[0]))
        .catch((err) => (errorMessage.value = err.message))
        .finally(() => (loading.value = false));
};
const createNewAPIKey = () => {
    createLoading.value = true;
    svc.createNewAPIKey(currentUserId)
        .then(() => getAPIKey())
        .catch((err) => (errorMessage.value = err.message))
        .finally(() => (createLoading.value = false));
};

getAPIKey();

const breadcrumbItems = [{ title: "User Preferences", to: "/user" }, { title: "Manage API Key" }];
</script>

<template>
    <section>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <span v-localize class="mb-2">
            An API key will allow you to access via web API. Please note that this key acts as an alternate means to
            access your account and should be treated with the same care as your login password.
        </span>

        <b-alert :show="errorMessage" dismissible fade variant="warning" @dismissed="errorMessage = null">
            {{ errorMessage }}
        </b-alert>

        <b-alert v-if="loading" class="m-2" show variant="info">
            <LoadingSpan message="Loading API keys" />
        </b-alert>

        <b-button
            v-else-if="!loading && !apiKey"
            :disabled="createLoading"
            class="create-button"
            variant="primary"
            @click.prevent="createNewAPIKey">
            <FontAwesomeIcon v-if="!createLoading" :icon="faPlus" />
            <FontAwesomeIcon v-else :icon="faSpinner" spin />
            <span v-localize>Create a new key</span>
        </b-button>

        <div v-else-if="apiKey" class="mx-2">
            <APIKeyItem :item="apiKey" @getAPIKey="getAPIKey" />
        </div>
    </section>
</template>

<style scoped>
.create-button {
    max-width: 10rem;
}
</style>
