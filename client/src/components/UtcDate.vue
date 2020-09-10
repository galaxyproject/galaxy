<template>
    <span class="utc-time" v-if="mode == 'date'" :title="elapsedTime">
        {{ fullDate }}
    </span>
    <span class="utc-time utc-time-elapsed" v-else :title="fullDate">
        {{ elapsedTime }}
    </span>
</template>

<script>
import moment from "moment";

export default {
    props: {
        date: {
            type: String,
            required: true,
        },
        mode: {
            type: String,
            default: "date", // or elapsed
        },
    },
    computed: {
        elapsedTime: function () {
            return moment(moment.utc(this.date)).from(moment().utc());
        },
        fullDate: function () {
            return moment.utc(this.date).format();
        },
    },
};
</script>
