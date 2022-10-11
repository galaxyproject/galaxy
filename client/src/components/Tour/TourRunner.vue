<template>
    <CenterFrame src="/welcome" />
</template>

<script>
import CenterFrame from "entry/analysis/modules/CenterFrame";
import { runTour } from "./runTour";

export default {
    components: {
        CenterFrame,
    },
    props: {
        tourId: {
            type: String,
            required: true,
        },
    },
    mounted() {
        runTour(this.tourId);
    },
};
</script>
