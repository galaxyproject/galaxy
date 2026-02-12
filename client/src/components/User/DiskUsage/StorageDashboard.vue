<script setup lang="ts">
import { BCard, BCardGroup } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";

import DiskUsageSummary from "./DiskUsageSummary.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import Heading from "@/components/Common/Heading.vue";

const router = useRouter();

const title = localize("Storage Dashboard");
const breadcrumbItems = [{ title }];

const cards = [
    {
        key: "free-space",
        title: localize("Is your usage more than expected?"),
        description: localize(
            "Find out what is eating up your space and learn how to easily and safely free up some of it.",
        ),
        icon: "fas fa-broom",
        buttonText: localize("Free up disk usage"),
        onClick: () => router.push({ name: "StorageManager" }),
    },
    {
        key: "explore-history",
        title: localize("Explore disk usage by history"),
        description: localize("Find out which histories or datasets take up the most space in your account."),
        icon: "fas fa-chart-pie",
        buttonText: localize("Explore now"),
        onClick: () => router.push({ name: "HistoriesOverview" }),
    },
    {
        key: "explore-storage",
        title: localize("Explore disk usage by storage"),
        description: localize("See how space in your account is distributed across storage locations."),
        icon: "fas fa-hdd",
        buttonText: localize("Explore now"),
        onClick: () => router.push({ name: "ObjectStoresOverview" }),
    },
];
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <Heading h2 size="sm">
            {{ localize("Here you can see an overview of your disk usage status.") }}
        </Heading>

        <DiskUsageSummary class="m-3" />

        <BCardGroup deck class="mx-3">
            <BCard
                v-for="card in cards"
                :key="card.key"
                :data-description="`${card.key} card`"
                class="d-flex flex-column">
                <h5 class="mb-2">
                    <i :class="card.icon" class="fa-lg mr-2" />
                    {{ card.title }}
                </h5>
                <p class="text-muted small flex-grow-1">{{ card.description }}</p>
                <GButton color="blue" @click="card.onClick">{{ card.buttonText }}</GButton>
            </BCard>
        </BCardGroup>
    </div>
</template>
