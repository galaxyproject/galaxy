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
        },
    },
    created() {
        this.initialize(this.date);
    },
    data: function () {
        return {
            processedDate: null,
        };
    },
    computed: {
        elapsedTime: function () {
            return moment(moment.utc(this.processedDate)).from(moment().utc());
        },
        fullDate: function () {
            return moment.utc(this.processedDate).format();
        },
    },
    watch: {
        date: function (newDate) {
            this.initialize(newDate);
        },
    },
    methods: {
        initialize: function (date) {
            if (this.customFormat) this.processedDate = moment(date, this.customFormat).format();
            else this.processedDate = date;
        },
    },
};
</script>
