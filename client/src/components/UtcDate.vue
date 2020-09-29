<template>
    <span class="utc-time" v-if="mode == 'date'" :title="elapsedTime">
        {{ fullDate }}
    </span>
    <span class="utc-time utc-time-elapsed" v-else-if="mode === 'elapsed'" :title="fullDate">
        {{ elapsedTime }}
    </span>
    <span class="utc-time" v-else :title="fullDate">
        {{ pretty }}
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
        customFormat: {
            type: String,
        },
    },
    created() {
        if (this.customFormat) this.processedDate = moment(this.date, this.customFormat).format();
        else this.processedDate = this.date;
    },
    computed: {
        elapsedTime: function () {
            return moment(moment.utc(this.processedDate)).from(moment().utc());
        },
        fullDate: function () {
            return moment.utc(this.processedDate).format();
        },
        pretty: function () {
            return moment.utc(this.processedDate).format("dddd MMM Do h:mm:ss YYYY [UTC]");
        },
    },
};
</script>
