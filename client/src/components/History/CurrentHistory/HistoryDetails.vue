<template>
    <Details
        :name="history.name"
        :annotation="history.annotation"
        :tags="history.tags"
        :writeable="writeable"
        @save="$emit('update:currentHistory', $event)">
        <template v-slot:name>
            <h3 data-description="history name display">{{ history.name || "History" }}</h3>
            <h5 v-if="history.size" class="history-size mt-1">
                <span>{{ history.size | niceFileSize }}</span>
            </h5>
        </template>
    </Details>
</template>

<script>
import prettyBytes from "pretty-bytes";
import { History } from "components/History/model";
import Details from "components/History/Layout/Details";

export default {
    components: {
        Details,
    },
    filters: {
        niceFileSize(rawSize = 0) {
            return prettyBytes(rawSize);
        },
    },
    props: {
        history: { type: History, required: true },
        writeable: { type: Boolean, default: true },
    },
};
</script>
