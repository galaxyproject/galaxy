<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ histories, handlers, historiesLoading }" :user="user">
            <div v-if="!historiesLoading && histories.length" id="histories" class="h-100 overflow-hidden">
                <b-container class="mt-1 mb-3">
                    <b-row>
                        <b-col>
                            <b-input-group>
                                <DebouncedInput v-slot="{ value, input }" v-model="historiesFilter">
                                    <b-form-input
                                        size="sm"
                                        :class="historiesFilter && 'font-weight-bold'"
                                        :value="value"
                                        :placeholder="'search histories' | localize"
                                        data-description="filter text input"
                                        @input="input"
                                        @keyup.esc="updateFilter('')" />
                                </DebouncedInput>
                                <b-input-group-append>
                                    <b-button
                                        size="sm"
                                        data-description="show deleted filter toggle"
                                        @click="updateFilter('')">
                                        <icon icon="times" />
                                    </b-button>
                                </b-input-group-append>
                            </b-input-group>
                        </b-col>

                        <b-col>
                            <b-input-group>
                                <DebouncedInput v-slot="{ value, input }" v-model="datasetsFilter">
                                    <b-form-input
                                        size="sm"
                                        :class="datasetsFilter && 'font-weight-bold'"
                                        :value="value"
                                        :placeholder="'search all datasets' | localize"
                                        data-description="filter text input"
                                        @input="input"
                                        @keyup.esc="updateFilter('')" />
                                </DebouncedInput>
                                <b-input-group-append>
                                    <b-button
                                        size="sm"
                                        data-description="show deleted filter toggle"
                                        @click="updateFilter('')">
                                        <icon icon="times" />
                                    </b-button>
                                </b-input-group-append>
                            </b-input-group>
                        </b-col>
                    </b-row>
                </b-container>

                <hr />

                <b-container fluid class="h-100 overflow-auto">
                    <virtual-list
                        class="row overflow-auto h-100"
                        :data-key="'id'"
                        :data-component="MultipleViewItem"
                        :data-sources="histories"
                        :direction="'horizontal'"
                        :item-class="'col-1 d-flex'"
                        :extra-props="{ handlers, onViewCollection }"
                        :wrap-class="'row flex-row flex-nowrap h-100'">
                    </virtual-list>
                </b-container>
            </div>
            <b-alert v-else class="m-2" variant="info" show>
                <LoadingSpan message="Loading Histories" />
            </b-alert>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import MultipleViewItem from "./MultipleViewItem";
import LoadingSpan from "components/LoadingSpan";
import VirtualList from "vue-virtual-scroll-list";
import DebouncedInput from "components/DebouncedInput";
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";

export default {
    components: {
        LoadingSpan,
        VirtualList,
        DebouncedInput,
        CurrentUser,
        UserHistories,
    },
    data() {
        return { MultipleViewItem: MultipleViewItem, datasetsFilter: "", historiesFilter: "" };
    },
    methods: {
        onViewCollection(collection) {},
        updateFilter(filter) {},
    },
};
</script>
