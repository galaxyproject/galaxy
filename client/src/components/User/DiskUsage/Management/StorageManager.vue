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

        <b-row class="justify-content-md-center mb-2">
            <h3>
                <b>Discarded Items</b>
            </h3>
        </b-row>
        <b-row class="justify-content-md-center mb-5">
            <b-card-group deck>
                <FreeableItemsSummary
                    :title="discardedDatasetsTitle"
                    :description="discardedDatasetsDescription"
                    :provider-callback="discardedDatasetProvider"
                    @onReviewItems="onDiscardedDatasetsReview" />
            </b-card-group>
        </b-row>
    </b-container>
</template>

<script>
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import { QuotaSettings } from "../model";
import FreeableItemsSummary from "./FreeableItemsSummary";
import { getDiscardedDatasets } from "./services";

export default {
    components: {
        FreeableItemsSummary,
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
            discardedDatasetsTitle: _l("Deleted datasets"),
            discardedDatasetsDescription: _l(
                "Datasets that you have marked as deleted but that haven't been permanently deleted." +
                    " You can restore these datasets or you can permanently remove them to free some space"
            ),
            largeDatasetsTitle: _l("Large datasets"),
            largeDatasetsDescription: _l("Datasets that haven't been deleted but are considerably large."),
            oldIDatasetsTitle: _l("Old datasets"),
            oldIDatasetsDescription: _l("Datasets that haven't been deleted but were not modified in quite some time."),
            intermediateDatasetsTitle: _l("Intermediate datasets"),
            intermediateDatasetsDescription: _l(
                "Datasets that were created as intermediate outputs by running a workflow." +
                    " Since these datasets can be easily recreated it may be safe to delete them"
            ),
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.userIdLocal = this.userId || Galaxy.user.id;
        this.quotaSettingsLocal = this.quotaSettings || QuotaSettings.create(Galaxy.config);
    },
    computed: {
        discardedDatasetProvider() {
            return getDiscardedDatasets;
        },
    },
    methods: {
        onDiscardedDatasetsReview(datasets) {
            console.log("Review datasets:", datasets);
        },
    },
};
</script>
