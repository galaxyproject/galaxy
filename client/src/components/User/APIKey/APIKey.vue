<template>
    <section class="api-key">
        <h2 v-localize>Manage API Keys</h2>

        <span v-localize>
            An API key will allow you to access via web API. Please note that this key acts as an alternate means to
            access your account and should be treated with the same care as your login password.
        </span>

        <b-alert dismissible fade variant="warning" :show="errorMessage" @dismissed="errorMessage = null">
            {{ errorMessage }}
        </b-alert>

        <b-container class="mt-2">
            <b-alert v-if="loading" class="m-2" variant="info" show>
                <LoadingSpan message="Loading API keys" />
            </b-alert>

            <b-row v-else-if="!loading && !items.length" class="text-center">
                <b-button variant="primary" :disabled="createLoading" @click.prevent="createNewAPIKey">
                    <icon v-if="!createLoading" icon="plus" />
                    <icon v-else icon="spinner" spin />
                    <span v-localize>Create a new key</span>
                </b-button>
            </b-row>

            <b-row v-else cols="1">
                <b-col class="mb-2">
                    <a-p-i-key-item :item="items[0]" @listAPIKeys="listAPIKeys" />
                </b-col>
            </b-row>
        </b-container>
    </section>
</template>

<script>
import svc from "./model/service";
import APIKeyItem from "./APIKeyItem";
import LoadingSpan from "components/LoadingSpan";

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
    mounted() {
        this.listAPIKeys();
    },
    methods: {
        listAPIKeys() {
            this.loading = true;

            svc.listAPIKeys()
                .then((items) => (this.items = items))
                .catch((err) => (this.errorMessage = err.message))
                .finally(() => (this.loading = false));
        },
        createNewAPIKey() {
            this.createLoading = true;

            svc.createNewAPIKey()
                .then(() => this.listAPIKeys())
                .catch((err) => (this.errorMessage = err.message))
                .finally(() => (this.createLoading = false));
        },
    },
};
</script>
