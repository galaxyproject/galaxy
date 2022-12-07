<template>
    <!-- Modal -->
    <transition name="modal">
        <div class="modal-mask">
            <div class="modal-wrapper">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h4 class="modal-title">Choose time</h4>
                            <button type="button" class="close" @click="close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <div class="modal-datetime">
                                <h2>Choose a starting date</h2>
                                <b-container class="bv-example-row">
                                    <b-row>
                                        <b-col>
                                            <datetime
                                                v-model="dateTimeVal"
                                                format="DD/MM/YYYY H:i:s"
                                                width="300px"
                                                >
                                            </datetime>
                                        </b-col>
                                        <b-col><button @click="alertVal">Alert current date value</button></b-col>
                                    </b-row>
                                </b-container>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </transition>
</template>

<script>
import datetime from "vuejs-datetimepicker";
export default{
    name:"DateTimeModal",
    components:{datetime},
     props:{
        openModal : Boolean
    },
    data() {
        return {
            dateTime: false,
            dateTimeVal: new Date().toLocaleString(),
        };
    },
    methods:{
     close: function(){
        console.log("clicked");
        this.$emit("closeModal");
        }
    }
}
</script>
<style>
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
    height: 70%;
}
</style>
