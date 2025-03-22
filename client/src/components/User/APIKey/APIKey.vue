<script setup>
import { getGalaxyInstance } from "app";
import LoadingSpan from "components/LoadingSpan";
import { ref } from "vue";

import APIKeyItem from "./APIKeyItem";
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
</script>

<template>
    <section class="api-key d-flex flex-column">
        <h1 v-localize class="h-lg">管理API密钥</h1>

        <span v-localize class="mb-2">
            API密钥将允许您通过Web API进行访问。请注意，此密钥作为访问您账户的替代方式，应与登录密码一样谨慎对待。
        </span>

        <b-alert :show="errorMessage" dismissible fade variant="warning" @dismissed="errorMessage = null">
            {{ errorMessage }}
        </b-alert>

        <b-alert v-if="loading" class="m-2" show variant="info">
            <LoadingSpan message="正在加载API密钥" />
        </b-alert>

        <b-button
            v-else-if="!loading && !apiKey"
            :disabled="createLoading"
            class="create-button"
            variant="primary"
            @click.prevent="createNewAPIKey">
            <icon v-if="!createLoading" icon="plus" />
            <icon v-else icon="spinner" spin />
            <span v-localize>创建新密钥</span>
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
