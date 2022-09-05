<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ histories, handlers, historiesLoading, currentHistory }" :user="user">
            <b-alert v-if="historiesLoading" class="m-2" variant="info" show>
                <LoadingSpan message="Loading Histories" />
            </b-alert>
            <div v-else-if="histories.length" class="multi-history-panel d-flex flex-column h-100">
                <b-input-group class="w-100">
                    <DebouncedInput v-slot="{ value, input }" v-model="filter">
                        <b-form-input
                            size="sm"
                            :class="filter && 'font-weight-bold'"
                            :value="value"
                            :placeholder="'search datasets in selected histories' | l"
                            data-description="filter text input"
                            @input="input"
                            @keyup.esc="updateFilter('')" />
                    </DebouncedInput>
                    <b-input-group-append>
                        <b-button size="sm" data-description="show deleted filter toggle" @click="updateFilter('')">
                            <icon icon="times" />
                        </b-button>
                    </b-input-group-append>
                </b-input-group>
                <multiple-view-list
                    :histories="histories"
                    :filter="filter"
                    :current-history="currentHistory"
                    :handlers="handlers" />
            </div>
            <b-alert v-else class="m-2" variant="danger" show>
                <span v-localize class="font-weight-bold">No History found.</span>
            </b-alert>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import DebouncedInput from "components/DebouncedInput";
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";
import MultipleViewList from "./MultipleViewList";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";

library.add(faTimes);

export default {
    components: {
        LoadingSpan,
        DebouncedInput,
        CurrentUser,
        UserHistories,
        MultipleViewList,
    },
    data() {
        return {
            filter: "",
        };
    },
    created() {
        return setTimeout(() => {
            document.getElementById("left").__vue__.hide();
        }, 1000);
    },
    methods: {
        updateFilter(filter) {
            this.filter = filter;
        },
    },
};
</script>
