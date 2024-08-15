export const commonJobFields = [
    { key: "id", label: "Encoded Job ID", sortable: true },
    { key: "decoded_job_id", label: "Decoded Job ID", sortable: true },
    { key: "user_email" },
    { key: "tool_id", label: "Tool", tdClass: ["break-word"] },
    { key: "state" },
    { key: "handler" },
    { key: "job_runner_name", label: "Job Runner" },
    { key: "external_id", label: "PID/Cluster ID", sortable: true },
];
