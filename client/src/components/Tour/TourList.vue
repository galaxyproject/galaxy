<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { ref } from "vue";

import { GalaxyApi } from "@/api";
import { withPrefix } from "@/utils/redirect";

import DelayedInput from "@/components/Common/DelayedInput.vue";

interface Tour {
    id: string;
    name?: string;
    description?: string;
    tags: string[];
}

const errorMessage = ref<string | null>(null);
const tours = ref<Tour[]>([]);
const searchQuery = ref("");

const onSearch = (newValue: string) => {
    searchQuery.value = newValue;
};

const match = (tour: Tour) => {
    const query = searchQuery.value.toLowerCase();
    return (
        !query ||
        (tour.id && tour.id.toLowerCase().includes(query)) ||
        (tour.name && tour.name.toLowerCase().includes(query)) ||
        (tour.description && tour.description.toLowerCase().includes(query)) ||
        (tour.tags && tour.tags.join().toLowerCase().includes(query))
    );
};

async function loadTours() {
    const { data, error } = await GalaxyApi().GET("/api/tours");
    if (error) {
        errorMessage.value = String(error);
    }
    tours.value = data as Tour[];
}

loadTours();
</script>

<template>
    <div>
        <h1 class="h-lg">Galaxy Tours</h1>
        <p>
            This page presents a list of interactive tours available on this Galaxy server. Select any tour to get
            started (and remember, you can click 'End Tour' at any time).
        </p>
        <h2 class="h-sm">Tours</h2>
        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <div v-else>
            <DelayedInput class="mb-3" :value="searchQuery" placeholder="search tours" :delay="0" @change="onSearch" />
            <div v-for="tour in tours" :key="tour.id">
                <div class="rounded border p-2 mb-2">
                    <a v-if="match(tour)" :href="withPrefix(`/tours/${tour.id}`)">
                        <div class="text-primary">{{ tour.name || tour.id }}</div>
                        <div v-html="tour.description" />
                        <div
                            v-for="(tag, index) in tour.tags"
                            :key="index"
                            class="badge badge-primary text-capitalize mr-1">
                            {{ tag }}
                        </div>
                    </a>
                </div>
            </div>
        </div>
    </div>
</template>
