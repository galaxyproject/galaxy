<template>
    <div>
        <b-table
            :fields="fields"
            :items="items"
            :filter="filter"
            hover
            responsive
            striped
            caption-top
            @row-clicked="toggleDetails"
            v-model="innerValue"
            :busy="busy">
            <template v-slot:table-caption>
                {{ tableCaption }}
            </template>
            <template v-slot:cell(update_time)="data">
                <utc-date :date="data.value" mode="elapsed" />
            </template>
            <template v-slot:row-details="row">
                <job-details :job="row.item" />
            </template>
            <template v-for="(index, name) in $slots" v-slot:[name]>
                <slot :name="name" />
            </template>
            <template v-for="(index, name) in $scopedSlots" v-slot:[name]="data">
                <slot :name="name" v-bind="data"></slot>
            </template>
        </b-table>
    </div>
</template>

<script>
import UtcDate from "components/UtcDate";
import JobDetails from "components/JobInformation/JobDetails";

export default {
    components: { UtcDate, JobDetails },
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
        filter: {
            type: String,
            required: true,
        },
        busy: {
            type: Boolean,
            required: true,
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
        toggleDetails(item) {
            this.$set(item, "_showDetails", !item._showDetails);
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
</style>
