<template>
    <b-container fluid>
        <b-link to="StorageDashboard">Back to Dashboard</b-link>
        <h2 class="text-center my-3">
            <b>{{ title }}</b>
        </h2>

        <b-row class="justify-content-md-center mb-5">
            <b-col md="auto">
                <b-alert v-if="quotaSettingsLocal.quotasEnabled" show>
                    {{ whatCountsText }}
                    <b-link :href="quotaSettingsLocal.quotasHelpUrl" target="_blank">{{ learnMoreText }}</b-link>
                </b-alert>
            </b-col>
        </b-row>

        <div v-for="(category, categoryIndex) in purgeableCategories" :key="categoryIndex">
            <b-row class="justify-content-md-center mb-2">
                <h3>
                    <b>{{ category.name }}</b>
                </h3>
            </b-row>
            <b-row class="justify-content-md-center mb-5">
                <b-card-group deck>
                    <PurgeableItemsSummary
                        v-for="(provider, providerIndex) in category.providers"
                        :key="providerIndex"
                        :category-name="category.name"
                        :provider-name="provider.name"
                        :description="provider.description"
                        :fetch-items="provider.fetchItems"
                        @onReviewItems="showReviewDialog" />
                </b-card-group>
            </b-row>
        </div>

        <PurgeableDetailsModal
            :title="currentProvider"
            :items="purgeableItems"
            @onConfirmPurgeSelectedItems="onConfirmPurgeSelected" />
    </b-container>
</template>

<script>
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import { QuotaSettings } from "../model";
import { categories } from "./categories";
import PurgeableItemsSummary from "./PurgeableItemsSummary";
import PurgeableDetailsModal from "./PurgeableDetailsModal";

export default {
    components: {
        PurgeableItemsSummary,
        PurgeableDetailsModal,
    },
    props: {
        userId: {
            type: String,
            required: false,
            default: null,
        },
        quotaSettings: {
            type: QuotaSettings,
            required: false,
            default: null,
        },
    },
    data() {
        return {
            userIdLocal: null,
            quotaSettingsLocal: null,
            errorMessage: null,
            title: _l("Manage your account storage"),
            whatCountsText: _l("The storage manager only shows files that count towards your disk quota."),
            learnMoreText: _l("Learn more"),
            purgeableCategories: [],
            purgeableItems: [],
            currentCategory: null,
            currentProvider: null,
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.userIdLocal = this.userId || Galaxy.user.id;
        this.quotaSettingsLocal = this.quotaSettings || QuotaSettings.create(Galaxy.config);
        this.purgeableCategories = categories;
    },
    methods: {
        showReviewDialog(items, category, provider) {
            this.purgeableItems = items;
            this.currentCategory = category;
            this.currentProvider = provider;
            this.$bvModal.show("purgeable-details-modal");
        },
        onConfirmPurgeSelected(items) {
            console.log("TODO Items confirmed: ", items);
        },
    },
};
</script>
