<template>
    <div class="jobs-table-wrapper">
        <GTable
            v-model="innerValue"
            :fields="fields"
            :items="items"
            hover
            responsive
            no-sort-reset
            striped
            caption-top
            :busy="busy"
            clickable-rows
            class="jobs-table"
            show-empty
            @row-click="onRowClick($event)">
            <template v-slot:table-caption>
                {{ tableCaption }}
            </template>

            <template v-slot:empty>
                <LoadingSpan v-if="loading" message="Loading jobs" />
                <BAlert v-else-if="!items || items.length === 0" class="no-jobs" variant="info" show>
                    {{ noItemsMessage }}
                </BAlert>
            </template>

            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>

            <template v-slot:row-details="row">
                <BCard>
                    <JobDetails :job="row.item" />
                </BCard>
            </template>

            <template v-slot:cell(user_email)="data">
                <GLink class="job-filter-link-user" :data-user="data.value" @click="$emit('user-clicked', data.value)">
                    {{ data.value }}
                </GLink>
            </template>

            <template v-slot:cell(tool_id)="data">
                <GLink
                    class="job-filter-link-tool-id"
                    :data-tool-id="data.value"
                    @click="$emit('tool-clicked', data.value)">
                    {{ data.value }}
                </GLink>
            </template>

            <template v-slot:cell(handler)="data">
                <GLink
                    class="job-filter-link-handler"
                    :data-handler="data.handler"
                    @click="$emit('handler-clicked', data.value)">
                    {{ data.value }}
                </GLink>
            </template>

            <template v-slot:cell(job_runner_name)="data">
                <GLink
                    class="job-filter-link-runner"
                    :data-runner="data.value"
                    @click="$emit('runner-clicked', data.value)">
                    {{ data.value }}
                </GLink>
            </template>

            <template v-for="(index, name) in $slots" v-slot:[name]>
                <slot :name="name" />
            </template>

            <template v-for="(index, name) in $scopedSlots" v-slot:[name]="data">
                <slot :name="name" v-bind="data"></slot>
            </template>
        </GTable>
    </div>
</template>

<script>
import { BAlert, BCard } from "bootstrap-vue";

import GLink from "@/components/BaseComponents/GLink.vue";
import GTable from "@/components/Common/GTable.vue";
import JobDetails from "@/components/JobInformation/JobDetails.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

export default {
    components: {
        BAlert,
        BCard,
        GLink,
        GTable,
        JobDetails,
        LoadingSpan,
        UtcDate,
    },
    props: {
        tableCaption: {
            type: String,
            required: true,
        },
        fields: {
            required: true,
        },
        items: {
            required: true,
        },
        busy: {
            type: Boolean,
            required: true,
        },
        loading: {
            type: Boolean,
            default: false,
        },
        noItemsMessage: {
            type: String,
            default: "No jobs to display.",
        },
        value: {},
    },
    data() {
        return {
            innerValue: this.value,
        };
    },
    watch: {
        innerValue(newVal) {
            this.$emit("input", newVal);
        },
        items(newVal) {
            this.setCellVariants(newVal);
        },
    },
    created() {
        this.setCellVariants(this.items);
    },
    methods: {
        setCellVariants(items) {
            items.forEach((item) => {
                item._cellVariants = { state: this.translateState(item.state) };
            });
        },
        onRowClick({ toggleDetails }) {
            toggleDetails();
        },
        translateState(state) {
            const translateDict = {
                ok: "success",
                error: "danger",
                new: "primary",
                queued: "secondary",
                running: "info",
                upload: "dark",
            };
            return translateDict[state] || "primary";
        },
    },
};
</script>

<style>
/* Can not be scoped because of command line tdClass */
.break-word {
    white-space: pre-wrap;
    word-break: break-word;
}
.info-frame-container {
    overflow: hidden;
    padding-top: 100%;
    position: relative;
}
.info-frame-container iframe {
    border: 0;
    height: 100%;
    left: 0;
    position: absolute;
    top: 0;
    width: 100%;
}
.jobs-table-wrapper {
    padding-bottom: 1em;
}
</style>
