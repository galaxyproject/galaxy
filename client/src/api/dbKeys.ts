/**
 * Historically, this API was used to get the list of genomes that were available
 * but now it is used to get the list of more generic "dbkeys".
 */

import { fetcher } from "@/api/schema";

export const dbKeysFetcher = fetcher.path("/api/genomes").method("get").create();
