<script setup lang="ts">
import { reactive } from "vue";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";

import DiskUsageSummary from "./DiskUsageSummary.vue";
import IconCard from "@/components/IconCard.vue";

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
    explore_by_history: {
        title: localize("Visually explore your disk usage by history"),
        description: localize(
            "Want to know what histories or datasets take up the most space in your account? Here you can explore your disk usage in a visual way by history."
        ),
        icon: "fas fa-chart-pie fa-6x",
        buttonText: localize("Explore now"),
    },
    explore_by_objectstore: {
        title: localize("Visually explore your disk usage by storage location"),
        description: localize(
            "Want to know how the space in your account is being distributed across storage locations? Here you can explore your disk usage in a visual way by where it is physically stored."
        ),
        icon: "fas fa-hdd fa-6x",
        buttonText: localize("Explore now"),
    },
});

function goToStorageManager() {
    router.push({ name: "StorageManager" });
}

function goToHistoriesOverview() {
    router.push({ name: "HistoriesOverview" });
}

function goToObjectStoresOverview() {
    router.push({ name: "ObjectStoresOverview" });
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
        <DiskUsageSummary class="m-3" />
        <IconCard
            class="mx-auto mb-3"
            data-description="free space card"
            :title="texts.freeSpace.title"
            :description="texts.freeSpace.description"
            :icon="texts.freeSpace.icon"
            :button-text="texts.freeSpace.buttonText"
            @onButtonClick="goToStorageManager" />

        <IconCard
            class="mx-auto mb-3"
            data-description="explore usage card"
            :title="texts.explore_by_history.title"
            :description="texts.explore_by_history.description"
            :icon="texts.explore_by_history.icon"
            :button-text="texts.explore_by_history.buttonText"
            @onButtonClick="goToHistoriesOverview" />

        <IconCard
            class="mx-auto mb-3"
            data-description="explore object store usage card"
            :title="texts.explore_by_objectstore.title"
            :description="texts.explore_by_objectstore.description"
            :icon="texts.explore_by_objectstore.icon"
            :button-text="texts.explore_by_objectstore.buttonText"
            @onButtonClick="goToObjectStoresOverview" />
    </div>
</template>
