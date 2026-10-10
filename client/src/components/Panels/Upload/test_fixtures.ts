import { http } from "@/api/client/__mocks__/http";
import { typesAndMappingHandler } from "@/components/Datatypes/test_fixtures";

/**
 * Requests the dataset upload methods make as they mount: genomes and the datatypes mapper
 * for every method, plus file sources and libraries for the two that browse. Sources and
 * libraries answer empty, so their methods show their "none available" notes.
 */
export const uploadMethodHandlers = {
    genomes: http.get("/api/genomes", ({ response }) => response(200).json([])),
    typesAndMapping: typesAndMappingHandler,
    fileSources: http.get("/api/remote_files/plugins", ({ response }) => response(200).json([])),
    libraries: http.get("/api/libraries", ({ response }) => response(200).json([])),
};
