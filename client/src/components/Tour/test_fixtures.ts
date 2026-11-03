import type { TourSummary } from "@/api/tours";

/** The tours Galaxy ships in `config/plugins/tours/`; each id is its file name without `.yaml`. */
export const CORE_TOURS: TourSummary[] = [
    {
        id: "core.deferred",
        name: "Deferred Data - An Introduction",
        description: "An introduction on how to work with deferred datasets.",
        tags: ["core", "UI"],
        requirements: ["new_history"],
    },
    {
        id: "core.galaxy_ui",
        name: "Galaxy UI",
        description: "A gentle introduction to the Galaxy User Interface",
        tags: ["core", "UI"],
        requirements: [],
    },
    {
        id: "core.history",
        name: "History Introduction",
        description: "A detailed introduction to the Galaxy History",
        tags: ["core", "history"],
        requirements: [],
    },
    {
        id: "core.visualizations",
        name: "Visualizations - Introduction",
        description: "An introduction on how to visualize datasets.",
        tags: ["core", "UI", "visualization"],
        requirements: ["new_history"],
    },
    {
        id: "core.windows",
        name: "Window Manager - Introduction",
        description: "An introduction on how to display multiple datasets and visualizations next to each other.",
        tags: ["core", "UI", "visualization"],
        requirements: ["new_history"],
    },
];

/** A tour an admin added to the server; tour descriptions may carry HTML. */
export const RNA_SEQ_TOUR: TourSummary = {
    id: "rna_seq_mapping",
    name: "RNA-seq Read Mapping",
    description: "Map paired-end reads with <b>HISAT2</b> and count reads per gene with featureCounts.",
    tags: ["training", "transcriptomics"],
    requirements: ["new_history"],
};
