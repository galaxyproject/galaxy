<template>
    <div id="dateTimeModal">
        <transition name="modal">
            <div class="modal-mask">
                <div class="modal-wrapper">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h4 class="modal-title">Choose time</h4>
                                <button type="button" class="close" @click="$emit('closeModal')">
                                    <span aria-hidden="true">&times;</span>
                                </button>
                            </div>
                            <div class="modal-body">
                                <div class="modal-datetime">
                                    <h2>Choose a starting date</h2>
                                    <b-container class="bv-example-row">
                                        <b-row>
                                            <b-col>
                                                <DatePicker v-model="date" mode="dateTime">
                                                    <template #default="{ inputValue, inputEvents }">
                                                        <input
                                                            class="px-3 py-1 border rounded"
                                                            :value="inputValue"
                                                            v-on="inputEvents" />
                                                    </template>
                                                </DatePicker>
                                            </b-col>
                                            <b-col
                                                ><button
                                                    id="confirmDate"
                                                    @click="
                                                        $emit('changeDate', date, 'confirmed');
                                                        $emit('closeModal');
                                                    ">
                                                    Confirm Date
                                                </button></b-col
                                            >
                                        </b-row>
                                    </b-container>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </transition>
    </div>
</template>

<script>
import { ref } from "vue";
import DatePicker from "v-calendar/lib/components/date-picker.umd";
import moment from "moment";

export default {
    name: "DateTimeModal",
    components: { DatePicker },
    props: {
        openModal: {
            type: Boolean,
            default: false,
        },
    },
    setup() {
        const date = ref(moment().format("YYYY-MM-DD HH:mm:ss"));
        return {
            date,
        };
    },
    // data() {
    //     return {
    //         date: moment().format("YYYY-MM-DD HH:mm:ss"),
    //     };
    // },
};
</script>
<style scoped>
.modal-mask {
    position: fixed;
    z-index: 10000;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: table;
}

.modal-wrapper {
    display: table-cell;
    vertical-align: middle;
}
.modal-dialog,
.modal-content {
    /* 80% of window height */
    height: 500px;
}
</style>
