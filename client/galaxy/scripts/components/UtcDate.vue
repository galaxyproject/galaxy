<template>
    <span class="utc-time" v-if="mode == 'date'" :title="elapsedTime">
        {{ full_date }}
    </span>
    <span class="utc-time utc-time-elapsed" v-else :title="full_date">
        {{ elapsedTime }}
    </span>
</template>

<script>
import moment from "moment";

export default {
    props: {
        date: {
            type: String,
            required: true
        },
        mode: {
            type: String,
            default: "date" // or elapsed
        }
    },
    computed: {
        elapsedTime: function() {
            return moment(moment.utc(this.date)).from(moment().utc());
        },
        full_date: function() {
            return moment.utc(this.date).format();
        }
    }
};
</script>
