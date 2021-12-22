<template>
    <div>
        <header class="main-header">
            <h1 class="text-center my-3">
                <b>{{ title }}</b>
            </h1>
            <h4 class="text-center my-3">{{ subtitle }}</h4>
        </header>

        <DiskUsageSummary class="m-3" :user-id="userId" :quota-settings="quotaSettings" />
        <IconCard
            class="mx-auto"
            :title="freeSpaceData.title"
            :description="freeSpaceData.description"
            :icon="freeSpaceData.icon"
            :button-text="freeSpaceData.buttonText"
            @onButtonClick="goToStorageManager" />
    </div>
</template>

<script>
import _l from "utils/localization";
import { QuotaSettings } from "./model";
import DiskUsageSummary from "components/User/DiskUsage/DiskUsageSummary";
import IconCard from "components/IconCard";

export default {
    components: {
        DiskUsageSummary,
        IconCard,
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
            freeSpaceData: {
                title: _l("Is your usage more than expected?"),
                description: _l(
                    "Find out what is eating up your space and learn how to easily and safely free up some of it."
                ),
                icon: "fas fa-broom fa-6x",
                buttonText: _l("Free up disk usage"),
            },
        };
    },
    created() {
        this.quotaSettings = QuotaSettings.create(this.config);
    },
    methods: {
        goToStorageManager() {
            console.log("TODO: go to storage manager");
        },
    },
};
</script>
