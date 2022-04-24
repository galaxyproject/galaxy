<template>
    <Details
        :name="history.name"
        :annotation="history.annotation"
        :tags="history.tags"
        :writeable="writeable"
        @save="onSave">
        <template v-slot:header>
            <nav v-if="history.size" class="history-size my-1 w-100 d-flex justify-content-between">
                <b-button
                    title="Access Dashboard"
                    variant="link"
                    size="sm"
                    class="text-decoration-none"
                    @click="onDashboard">
                    <icon icon="database" />
                    <span>{{ history.size | niceFileSize }}</span>
                </b-button>
                <b-button-group>
                    <b-button
                        title="Show active"
                        variant="link"
                        size="sm"
                        class="text-decoration-none"
                        @click="setFilter('')">
                        <icon icon="star" />
                        <span>{{ history.contents_active.active }}</span>
                    </b-button>
                    <b-button
                        v-if="history.contents_active.deleted"
                        title="Show deleted"
                        variant="link"
                        size="sm"
                        class="text-decoration-none"
                        @click="setFilter('deleted=true')">
                        <icon icon="trash" />
                        <span>{{ history.contents_active.deleted }}</span>
                    </b-button>
                    <b-button
                        v-if="history.contents_active.hidden"
                        title="Show hidden"
                        variant="link"
                        size="sm"
                        class="text-decoration-none"
                        @click="setFilter('visible=false')">
                        <icon icon="lock" />
                        <span>{{ history.contents_active.hidden }}</span>
                    </b-button>
                </b-button-group>
            </nav>
        </template>
        <template v-slot:name>
            <h3 data-description="name display" class="my-2" v-short="history.name || 'History'" />
        </template>
    </Details>
</template>

<script>
import { backboneRoute } from "components/plugins/legacyNavigation";
import prettyBytes from "pretty-bytes";
import short from "components/directives/v-short";
import Details from "components/History/Layout/Details";

export default {
    components: {
        Details,
    },
    directives: {
        short,
    },
    filters: {
        niceFileSize(rawSize = 0) {
            return prettyBytes(rawSize);
        },
    },
    props: {
        history: { type: Object, required: true },
        writeable: { type: Boolean, default: true },
    },
    methods: {
        onDashboard() {
            backboneRoute("/storage");
        },
        onSave(newDetails) {
            const id = this.history.id;
            this.$emit("updateHistory", { ...newDetails, id });
        },
        setFilter(newFilterText) {
            this.$emit("update:filter-text", newFilterText);
        },
    },
};
</script>
