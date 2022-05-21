<template>
    <span v-if="mode == 'date'" class="utc-time" :title="elapsedTime">
        {{ fullISO }}
    </span>
    <span v-else-if="mode === 'elapsed'" class="utc-time utc-time-elapsed" :title="fullISO">
        {{ elapsedTime }}
    </span>
    <span v-else class="utc-time" :title="elapsedTime">
        {{ pretty }}
    </span>
</template>

<script>
import { formatDistanceToNow, parse, parseISO } from "date-fns";
import { formatInTimeZone } from "date-fns-tz";

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
            return formatDistanceToNow(this.parsedDate, { addSuffix: true });
        },
        fullISO: function () {
            return this.parsedDate.toISOString();
        },
        parsedDate: function () {
            if (this.customFormat !== undefined) {
                return parse(this.date, this.customFormat, new Date());
            } else {
                // assume ISO format date, except in Galaxy this won't have TZinfo -- it will always be Zulu
                return parseISO(`${this.date}Z`);
            }
        },
        pretty: function () {
            return `${formatInTimeZone(this.parsedDate, "Etc/Zulu", "eeee MMM do H:mm:ss yyyy")} UTC`;
        },
    },
};
</script>
