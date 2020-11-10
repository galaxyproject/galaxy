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
        customFormat: {
            type: String,
            default: null,
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
            if (this.customFormat) {
                return moment(this.date, this.customFormat).format();
            } else {
                return this.date;
            }
        },
    },
};
</script>
