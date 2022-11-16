<template>
    <div>
        <svg id="gantt"></svg>
        <button id="view" @click="changeQDayView">Quarter Day View</button>
        <button id="view" @click="changeHDayView">Half Day View</button>
        <button id="view" @click="changeDayView">Day View</button>
        <button id="view" @click="changeWeekView">Week View</button>
        <button id="view" @click="changeMonthView">Month View</button>
        <button id="view" @click="changeHourView">Hour View</button>
        <button id="view" @click="changeMinuteView">Minute View</button>
    </div>
</template>

<script>
import Gantt from "../../../../node_modules/frappe-gantt";
import store from "../../../store";
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";

export default {
    name: "Gantt",
    computed: {
        ...mapGetters({
            currentHistory: "history/currentHistoryId",
        }),
    },
    data() {
        return {
            tasks: [],
            historyId: null,
            accountingArray: [],
            colors: ['one', 'two', 'three', 'four']
        };
    },
    computed: {
        ...mapGetters({
            currentHistory: "history/currentHistoryId",
        }),
    },
    watch: {
        accountingArray(newArray, oldArray) {
            if (newArray.length > 0) {
                var entries = [];
                newArray.map((row, idx) => {
                    entries.push({
                        id: idx.toString(),
                        name: row["label"],
                        start: row["startTime"],
                        end: row["endTime"],
                        progress: 100,
                        custom_class: this.colors[idx%4]
                    });
                });
                this.gantt = new Gantt("#gantt", entries, {
                    view_mode: "Day",
                    view_modes: ["Quarter Day", "Half Day", "Day", "Week", "Month", "Hour", "Minute"],
                    arrow_curve: 14,
                    date_format: "YYYY-MM-DD",
                    popup_trigger:"mouseover",
                    custom_popup_html: function (task) {
                        return `
          <div class="details-container">
            <h5>${task.name}</h5>
            <p>Started At: ${task.start}</p>
            <p>Finished At: ${task.end}</p>
            <p>100% completed!</p>
          </div>
        `;
                    },
                });
            }
        },
    },
    mounted() {
        this.historyId = this.currentHistory;
        this.getData();
    },

    methods: {
        ...mapCacheActions(["fetchJobMetricsForJobId", "storeIntoAccountingArray"]),
        getData: function () {
            const historyItems = store.getters.getHistoryItems({ historyId: this.historyId, filterText: "" });
            historyItems
                ? historyItems.forEach(async (job) => {
                      var Accounting = {};
                      // console.log('Job is ', job)
                      if (job.id) {
                          await this.fetchJobMetricsForJobId(job.id);
                          const metrics = await this.$store.state?.jobMetrics?.jobMetricsByJobId[`${job.id}`];
                          if (metrics && metrics[1] && metrics[2]) {
                              Accounting = {
                                  label: job.name,
                                  id: job.hid,
                                  jobid: job.id,
                                  startTime: metrics[1].value,
                                  endTime: metrics[2].value,
                              };
                              this.accountingArray.push(Accounting);
                          }
                          // console.log('Accounting and array ', Accounting, this.accountingArray)
                      }
                  })
                : null;
            // console.log('Accounting Items from Gantt.vue are ', this.accountingArray)
        },
        changeQDayView: function () {
            this.gantt.change_view_mode("Quarter Day");
        },
        changeHDayView: function () {
            this.gantt.change_view_mode("Half Day");
        },
        changeDayView: function () {
            this.gantt.change_view_mode("Day");
        },
        changeWeekView: function () {
            this.gantt.change_view_mode("Week");
        },
        changeMonthView: function () {
            this.gantt.change_view_mode("Month");
        },
        changeHourView: function () {
            this.gantt.change_view_mode("Hour");
        },
        changeMinuteView: function () {
            this.gantt.change_view_mode("Minute");
        },
    },
};
</script>

<style>
.gantt .tick {
    stroke: #666;
}

.one .bar {
    fill: #ff8e76 !important;
}

.one .bar-progress {
    fill: #d95b43 !important;
}

.two .bar {
    fill: #87576a !important;
}

.two .bar-progress {
    fill: #542437 !important;
}

.three .bar {
    fill: #86aaad !important;
}

.three .bar-progress {
    fill: #53777a !important;
}

.four .bar {
    fill: #f35c75 !important;
}

.four .bar-progress {
    fill: #c02942 !important;
}
</style>
