<template>
    <div>
        <b-input-group>
            <DebouncedInput v-model="filterText" v-slot="{ value, input }">
                <b-form-input
                    size="sm"
                    :value="value"
                    @input="input"
                    :placeholder="'search datasets' | localize"
                    data-description="filter text input" />
            </DebouncedInput>
            <b-input-group-append>
                <b-button
                    size="sm"
                    :pressed="showDeleted"
                    :variant="showDeleted ? 'info' : 'secondary'"
                    @click="showDeleted = !showDeleted"
                    data-description="show deleted filter toggle">
                    <icon icon="trash" />
                </b-button>
                <b-button
                    size="sm"
                    :pressed="showAdvanced"
                    :variant="showAdvanced ? 'info' : 'secondary'"
                    @click="onToggle"
                    data-description="show advanced filter toggle">
                    <icon v-if="showAdvanced" icon="angle-double-up" />
                    <icon v-else icon="angle-double-down" />
                </b-button>
                <b-button size="sm" @click="filterText = ''" data-description="show deleted filter toggle">
                    <icon icon="times" />
                </b-button>
            </b-input-group-append>
        </b-input-group>
        <div v-if="showAdvanced" class="mt-2">
            <small>Filter by name:</small>
            <b-form-input v-model="filterAdvanced['name=']" size="sm" placeholder="any name" />
            <small class="mt-1">Filter by extension:</small>
            <b-form-input v-model="filterAdvanced['extension=']" size="sm" placeholder="any extension" />
            <small class="mt-1">Filter by tag:</small>
            <b-form-input v-model="filterAdvanced['tag=']" size="sm" placeholder="any tag" />
            <small class="mt-1">Filter by state:</small>
            <b-form-input v-model="filterAdvanced['state=']" size="sm" placeholder="any state" />
            <small class="mt-1">Filter by item index:</small>
            <b-form-group class="m-0">
                <b-input-group>
                    <b-form-input v-model="filterAdvanced['hid>']" size="sm" placeholder="index greater" />
                    <b-form-input v-model="filterAdvanced['hid<']" size="sm" placeholder="index lower" />
                </b-input-group>
            </b-form-group>
            <small class="mt-1">Filter by creation time:</small>
            <b-form-group>
                <b-input-group>
                    <b-form-input v-model="filterAdvanced['create_time>']" size="sm" placeholder="created after" />
                    <b-form-input v-model="filterAdvanced['create_time<']" size="sm" placeholder="created before" />
                </b-input-group>
            </b-form-group>
            <b-button class="mr-1" @click="onSearch" size="sm" variant="primary">
                <icon icon="search" />
                <span>{{ "Search" | localize }}</span>
            </b-button>
            <b-button size="sm" @click="onToggle">
                <icon icon="redo" />
                <span>{{ "Cancel" | localize }}</span>
            </b-button>
        </div>
    </div>
</template>

<script>
import DebouncedInput from "components/DebouncedInput";

export default {
    components: {
        DebouncedInput,
    },
    props: {
        params: { type: Object, required: true },
        showAdvanced: { type: Boolean, default: false },
    },
    data() {
        return {
            filterAdvanced: {
                "create_time>": null,
                "create_time<": null,
                "extension=": null,
                "hid>": null,
                "hid<": null,
                "name=": null,
                "state=": null,
                "tag=": null,
            },
        };
    },
    computed: {
        filterText: {
            get() {
                return this.params.filterText;
            },
            set(newVal) {
                const newParams = Object.assign({}, this.params);
                newParams.filterText = newVal;
                this.updateParams(newParams);
            },
        },
        showDeleted: {
            get() {
                return this.params.showDeleted;
            },
            set(newFlag) {
                const newParams = Object.assign({}, this.params);
                newParams.showDeleted = newFlag;
                this.updateParams(newParams);
            },
        },
        showHidden: {
            get() {
                return this.params.showHidden;
            },
            set(newFlag) {
                const newParams = Object.assign({}, this.params);
                newParams.showHidden = newFlag;
                this.updateParams(newParams);
            },
        },
    },
    methods: {
        onSearch() {
            const newParams = Object.assign({}, this.params);
            let newFilterText = "";
            Object.entries(this.filterAdvanced).filter(([key, value]) => {
                if (value) {
                    if (newFilterText) {
                        newFilterText += " ";
                    }
                    newFilterText += `${key}'${value}'`;
                }
            });
            newParams.filterText = newFilterText;
            this.updateParams(newParams);
            this.onToggle();
        },
        onToggle() {
            this.$emit("update:show-advanced", !this.showAdvanced);
        },
        updateParams(newParams) {
            this.$emit("update:params", newParams);
        },
    },
};
</script>
