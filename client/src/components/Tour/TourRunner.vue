<template>
    <CenterPanel src="welcome" />
</template>

<script>
import CenterPanel from "entry/analysis/modules/CenterPanel";
import { runTour } from "./runTour";

export default {
    components: {
        CenterPanel,
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
