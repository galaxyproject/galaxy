import { fetcher } from "@/api/schema";

export const fetchGenomes = fetcher.path("/api/genomes").method("get").create();
