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
                    <b>{{ category.title }}</b>
                </h3>
            </b-row>
            <b-row class="justify-content-md-center mb-5">
                <b-card-group deck>
                    <PurgeableItemsSummary
                        v-for="(provider, providerIndex) in category.providers"
                        :key="providerIndex"
                        :title="provider.title"
                        :description="provider.description"
                        :provider-callback="provider.fetchCallback"
                        @onReviewItems="provider.reviewCallback" />
                </b-card-group>
            </b-row>
        </div>
    </b-container>
</template>

<script>
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import { QuotaSettings } from "../model";
import { fetchDiscardedDatasets } from "./services";
import PurgeableItemsSummary from "./PurgeableItemsSummary";

export default {
    components: {
        PurgeableItemsSummary,
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
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.userIdLocal = this.userId || Galaxy.user.id;
        this.quotaSettingsLocal = this.quotaSettings || QuotaSettings.create(Galaxy.config);
        this.loadCategories();
    },
    methods: {
        onReview(items) {
            console.log("Review datasets:", items);
            this.purgeableItems = items;
        },
        loadCategories() {
            this.purgeableCategories = [
                {
                    title: _l("Discarded Items"),
                    providers: [
                        {
                            title: _l("Deleted datasets"),
                            description: _l(
                                "Datasets that you have marked as deleted but that haven't been permanently deleted." +
                                    " You can restore these datasets or you can permanently remove them to free some space"
                            ),
                            fetchCallback: fetchDiscardedDatasets,
                            reviewCallback: (items) => this.onReview(items),
                        },
                    ],
                },
            ];
        },
    },
};
</script>
