<script setup>
import { ref } from "vue";
import svc from "./model/service";
import APIKeyItem from "./APIKeyItem";
import { getGalaxyInstance } from "app";
import LoadingSpan from "components/LoadingSpan";

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
</script>

<template>
    <section class="api-key d-flex flex-column">
        <h1 v-localize class="h-lg">Manage API Key</h1>

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
            <icon v-if="!createLoading" icon="plus" />
            <icon v-else icon="spinner" spin />
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
