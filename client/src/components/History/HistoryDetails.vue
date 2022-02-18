<template>
    <HeaderDetails
        :name="history.name"
        :annotation="history.annotation"
        :tags="history.tags"
        :writeable="writeable"
        @save="$emit('update:currentHistory', $event)">
        <template v-slot:name>
            <h3 data-description="history name display">{{ history.name || "(History Name)" }}</h3>
            <h5 class="history-size">
                <span v-if="history.size">{{ history.size | niceFileSize }}</span>
                <span v-else v-localize>(empty)</span>
            </h5>
        </template>
    </HeaderDetails>
</template>

<script>
import prettyBytes from "pretty-bytes";
import { History } from "./model";
import HeaderDetails from "./HeaderDetails";

export default {
    components: {
        HeaderDetails,
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
