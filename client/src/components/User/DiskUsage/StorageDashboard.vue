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
import { getGalaxyInstance } from "app";
import { QuotaSettings } from "./model";
import DiskUsageSummary from "components/User/DiskUsage/DiskUsageSummary";
import IconCard from "components/IconCard";

export default {
    components: {
        DiskUsageSummary,
        IconCard,
    },
    data() {
        return {
            title: _l("Storage Dashboard"),
            subtitle: _l("Here you can see an overview of your disk usage status."),
            userId: null,
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
        const Galaxy = getGalaxyInstance();
        this.userId = Galaxy.user.id;
        this.quotaSettings = QuotaSettings.create(Galaxy.config);
    },
    methods: {
        goToStorageManager() {
            this.$router.push({
                name: "StorageManager",
                params: { userId: this.userId, quotaSettings: this.quotaSettings },
            });
        },
    },
};
</script>
