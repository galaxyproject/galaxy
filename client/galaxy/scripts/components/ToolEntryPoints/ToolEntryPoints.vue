<template>
    <div class="infomessagelarge">
        <p v-if="entryPoints.length==0" >
            Waiting for RealTimeTool result view(s) to become available.
        </p>
        <p v-else-if="entryPoints.length==1" >
            <span v-if="entryPoints[0].active" >
                There is a RealTimeTool result view available, click here to display.
            </span>
            <span v-else>
                There is a RealTimeTool result view available, waiting for view to become active...
            </span>
        </p>
        <p v-else>
            There is are multiple RealTimeTool result views available:
            <ul>
                <li v-for="entryPoint of entryPoints" v-bind:key="entryPoint.id" >
                    {{ entryPoint.name }}
                    <span v-if="entryPoint.active">
                        (active)
                    </span>
                    <span v-else>
                        (waiting to become active...)
                    </span>
                </li>
            </ul>
        </p>

        You may also access all active RealTimeTools from the User menu.
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
export default {
    props: {
        jobId: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            entryPoints: [],
            interval: null,
        };
    },
    created: function() {
        this.reloadEntryPoints();
    },
    beforeDestroy: function(){
        clearInterval(this.interval);
    },
    methods: {
        reloadEntryPoints: function() {
            clearInterval(this.interval);
            const url = getAppRoot() + `api/entry_points?job_id=${this.jobId}`;
            axios
                .get(url)
                .then(response => {
                    const entryPoints = [];
                    let allReady = true;
                    response.data.forEach((entryPoint, i) => {
                        entryPoints.push(entryPoint);
                        if(! entryPoint.active) {
                            allReady = false;
                        }
                    });
                    this.entryPoints = entryPoints;
                    if(! allReady || entryPoints.length == 0) {
                        this.interval = setInterval(() => {
                            this.reloadEntryPoints();
                        }, 5000);
                    }
                })
                .catch(e => {
                    console.error(e);
                });
        }
    }
};
</script>