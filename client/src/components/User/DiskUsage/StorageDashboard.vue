<script setup lang="ts">
import localize from "@/utils/localization";
import DiskUsageSummary from "./DiskUsageSummary.vue";
import IconCard from "@/components/IconCard.vue";
import { reactive } from "vue";
import { useRouter } from "vue-router/composables";

const router = useRouter();

const texts = reactive({
    title: localize("Storage Dashboard"),
    subtitle: localize("Here you can see an overview of your disk usage status."),
    freeSpace: {
        title: localize("Is your usage more than expected?"),
        description: localize(
            "Find out what is eating up your space and learn how to easily and safely free up some of it."
        ),
        icon: "fas fa-broom fa-6x",
        buttonText: localize("Free up disk usage"),
    },
    explore: {
        title: localize("Visually explore your disk usage"),
        description: localize(
            "Want to know what histories or datasets take up the most space in your account? Here you can explore your disk usage in a visual way."
        ),
        icon: "fas fa-chart-pie fa-6x",
        buttonText: localize("Explore now"),
    },
});

function goToStorageManager() {
    router.push({ name: "StorageManager" });
}

function goToHistoriesOverview() {
    router.push({ name: "HistoriesOverview" });
}
</script>

<template>
    <div>
        <header class="main-header">
            <h1 class="text-center my-3">
                <b>{{ texts.title }}</b>
            </h1>
            <h2 class="text-center my-3 h-sm">{{ texts.subtitle }}</h2>
        </header>
        <disk-usage-summary class="m-3" />
        <icon-card
            class="mx-auto mb-3"
            data-description="free space card"
            :title="texts.freeSpace.title"
            :description="texts.freeSpace.description"
            :icon="texts.freeSpace.icon"
            :button-text="texts.freeSpace.buttonText"
            @onButtonClick="goToStorageManager" />

        <icon-card
            class="mx-auto mb-3"
            data-description="explore usage card"
            :title="texts.explore.title"
            :description="texts.explore.description"
            :icon="texts.explore.icon"
            :button-text="texts.explore.buttonText"
            @onButtonClick="goToHistoriesOverview" />
    </div>
</template>
