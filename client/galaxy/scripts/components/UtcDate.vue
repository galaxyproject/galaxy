<template>
    <span class="utc-time" v-if="mode == 'date'" :title="elapsedTime">
        {{ date }}
    </span>
    <span class="utc-time utc-time-elapsed" v-else :title="date">
        {{ elapsedTime }}
    </span>
</template>

<script>
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
            var utcUpdate = new Date(this.date);
            var now = new Date();
            var utcNow = new Date(
                now.getUTCFullYear(),
                now.getUTCMonth(),
                now.getUTCDate(),
                now.getUTCHours(),
                now.getUTCMinutes(),
                now.getUTCSeconds(),
                now.getUTCMilliseconds()
            );
            const timeDiff = utcNow - utcUpdate;
            const daysDiff = timeDiff / (1000 * 3600 * 24);
            const hoursDiff = timeDiff / (1000 * 3600);
            const minutesDiff = timeDiff / (1000 * 60);
            let diffStr;
            if (daysDiff >= 1) {
                diffStr = `${Math.floor(daysDiff)} days ago`;
            } else if (hoursDiff >= 1) {
                diffStr = `${Math.floor(hoursDiff)} hours ago`;
            } else {
                diffStr = `${Math.floor(minutesDiff)} minutes ago`;
            }
            return diffStr;
        }
    }
};
</script>
