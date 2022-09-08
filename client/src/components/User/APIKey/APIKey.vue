<template>
    <section class="api-key d-flex flex-column">
        <h2 v-localize>Manage API Key</h2>

        <span v-localize class="mb-2">
            An API key will allow you to access via web API. Please note that this key acts as an alternate means to
            access your account and should be treated with the same care as your login password.
        </span>

        <b-alert dismissible fade variant="warning" :show="errorMessage" @dismissed="errorMessage = null">
            {{ errorMessage }}
        </b-alert>

        <b-alert v-if="loading" class="m-2" variant="info" show>
            <LoadingSpan message="Loading API keys" />
        </b-alert>

        <b-button
            v-else-if="!loading && !items.length"
            variant="primary"
            :disabled="createLoading"
            class="create-button"
            @click.prevent="createNewAPIKey">
            <icon v-if="!createLoading" icon="plus" />
            <icon v-else icon="spinner" spin />
            <span v-localize>Create a new key</span>
        </b-button>

        <b-container v-else-if="items.length" class="mt-2">
            <b-row cols="1">
                <b-col v-for="(item, index) in items" :key="index" class="mb-2">
                    <APIKeyItem :item="item" @listAPIKeys="listAPIKeys" />
                </b-col>
            </b-row>
        </b-container>
    </section>
</template>

<script>
import svc from "./model/service";
import APIKeyItem from "./APIKeyItem";
import LoadingSpan from "components/LoadingSpan";
import { getGalaxyInstance } from "app";

export default {
    components: {
        APIKeyItem,
        LoadingSpan,
    },
    data() {
        return {
            items: [],
            loading: false,
            createLoading: false,
            errorMessage: null,
        };
    },
    computed: {
        currentUserId() {
            return getGalaxyInstance().user.id;
        },
    },
    mounted() {
        this.listAPIKeys();
    },
    methods: {
        listAPIKeys() {
            this.loading = true;

            svc.listAPIKeys(this.currentUserId)
                .then((items) => (this.items = items))
                .catch((err) => (this.errorMessage = err.message))
                .finally(() => (this.loading = false));
        },
        createNewAPIKey() {
            this.createLoading = true;

            svc.createNewAPIKey(this.currentUserId)
                .then(() => this.listAPIKeys())
                .catch((err) => (this.errorMessage = err.message))
                .finally(() => (this.createLoading = false));
        },
    },
};
</script>

<style scoped>
.create-button {
    max-width: 10rem;
}
</style>
