<template>
    <div>
        <h1 class="h-lg">Galaxy Tours</h1>
        <p>
            This page presents a list of interactive tours available on this Galaxy server. Select any tour to get
            started (and remember, you can click 'End Tour' at any time).
        </p>
        <h2 class="h-sm">Tours</h2>
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <DelayedInput class="mb-3" :value="search" :placeholder="searchTours" :delay="0" @change="onSearch" />
            <div v-for="tour in tours" :key="tour.id">
                <div class="rounded border p-2 mb-2">
                    <a v-if="match(tour)" :href="`/tours/${tour.id}`">
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

<script>
import DelayedInput from "components/Common/DelayedInput";
import { getAppRoot } from "onload/loadConfig";
import _l from "utils/localization";
import { urlData } from "utils/url";

export default {
    components: {
        DelayedInput,
    },
    data() {
        return {
            tours: [],
            search: "",
            error: null,
            searchTours: _l("search tours"),
        };
    },
    created() {
        this.root = getAppRoot();
        urlData({ url: `/api/tours` })
            .then((response) => {
                this.tours = response;
            })
            .catch((error) => {
                this.error = error;
            });
    },
    methods: {
        onSearch(newValue) {
            this.search = newValue;
        },
        onTour(tourId) {
            window.location.href = `/tours/${tourId}`;
        },
        match(tour) {
            const query = this.search.toLowerCase();
            return (
                !query ||
                (tour.id && tour.id.toLowerCase().includes(query)) ||
                (tour.name && tour.name.toLowerCase().includes(query)) ||
                (tour.description && tour.description.toLowerCase().includes(query)) ||
                (tour.tags && tour.tags.join().toLowerCase().includes(query))
            );
        },
    },
};
</script>
