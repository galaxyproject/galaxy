<template>
    <div class="infomessagelarge">
        <p v-if="entryPoints.length==0" >
            Waiting for RealTimeTool result view(s) to become available.
        </p>
        <p v-else-if="entryPoints.length==1" >
            <span v-if="entryPoints[0].active" >
                There is a RealTimeTool result view available, <a :href="entryPoints[0].target">click here to display</a>.
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
                        (<a :href="entryPoints[0].target">click here to display</a>)
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
import { clearPolling, pollUntilActive } from "mvc/entrypoints/poll";
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
        };
    },
    created: function() {
        this.pollEntryPoints();
    },
    beforeDestroy: function(){
        clearPolling();
    },
    methods: {
        pollEntryPoints: function() {
            const onUpdate = (entryPoints) => {
                this.entryPoints = entryPoints;
            }
            const onError = (e) => {
                console.error(e);
            }
            pollUntilActive(onUpdate, onError, {"job_id": this.jobId})
        }
    }
};
</script>
