<template>
    <span class="utc-time" v-if="mode == 'date'" :title="elapsedTime">
        {{ fullDate }}
    </span>
    <span class="utc-time utc-time-elapsed" v-else-if="mode === 'elapsed'" :title="fullDate">
        {{ elapsedTime }}
    </span>
    <span class="utc-time" v-else :title="elapsedTime">
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
            default: undefined,
        },
    },
    computed: {
        elapsedTime: function () {
            return moment(moment.utc(this.formattedDate)).from(moment().utc());
        },
        fullDate: function () {
            return moment.utc(this.formattedDate).format();
        },
        formattedDate: function () {
            if (this.customFormat !== undefined) {
                return moment(this.date, this.customFormat).format();
            } else {
                return this.date;
            }
        },
        pretty: function () {
            return moment.utc(this.formattedDate).format("dddd MMM Do h:mm:ss YYYY [UTC]");
        },
    },
};
</script>
