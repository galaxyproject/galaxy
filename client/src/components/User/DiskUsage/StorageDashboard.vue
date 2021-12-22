<template>
    <div>
        <header class="main-header">
            <h1 class="text-center my-3">
                <b>{{ title }}</b>
            </h1>
            <h4 class="text-center my-3">{{ subtitle }}</h4>
        </header>
        <b-row class="justify-content-md-center mb-5">
            <DiskUsageSummary :user-id="userId" :quota-settings="quotaSettings" />
        </b-row>
    </div>
</template>

<script>
import _l from "utils/localization";
import { QuotaSettings } from "./model";
import DiskUsageSummary from "components/User/DiskUsage/DiskUsageSummary";

export default {
    components: {
        DiskUsageSummary,
    },
    props: {
        userId: {
            type: String,
            required: true,
        },
        config: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            title: _l("Storage Dashboard"),
            subtitle: _l("Here you can see an overview of your disk usage status."),
            quotaSettings: null,
        };
    },
    created() {
        this.quotaSettings = QuotaSettings.create(this.config);
    },
};
</script>
