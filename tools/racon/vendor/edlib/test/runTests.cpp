#include <cstdio>
#include <ctime>
#include <cstdlib>
#include <cstring>

#include "edlib.h"
#include "SimpleEditDistance.h"

using namespace std;


bool runRandomTests(int numTests, EdlibAlignMode mode, bool findAlignment);
bool runTests();

int calcEditDistanceSimple(const char* query, int queryLength,
                           const char* target, int targetLength,
                           EdlibAlignMode mode, int* score,
                           int** positions, int* numPositions);

bool checkAlignment(const char* query, int queryLength,
                    const char* target,
                    int score, int pos, EdlibAlignMode mode,
                    unsigned char* alignment, int alignmentLength);

int getAlignmentStart(const unsigned char* alignment, int alignmentLength,
                      int endLocation);

int max(int a, int b) {
    return a > b ? a : b;
}

int main(int argc, char* argv[]) {
    // This program has optional first parameter, which is number of random tests to run
    // per each algorithm. Default is 100.
    int numRandomTests = 100;
    if (argc > 1) {
        numRandomTests = (int) strtol(argv[1], NULL, 10);
    }

    srand(42);
    bool allTestsPassed = true;

    printf("Testing HW with alignment...\n");
    allTestsPassed &= runRandomTests(numRandomTests, EDLIB_MODE_HW, true);
    printf("\n");

    printf("Testing HW...\n");
    allTestsPassed &= runRandomTests(numRandomTests, EDLIB_MODE_HW, false);
    printf("\n");

    printf("Testing NW with alignment...\n");
    allTestsPassed &= runRandomTests(numRandomTests, EDLIB_MODE_NW, true);
    printf("\n");

    printf("Testing NW...\n");
    allTestsPassed &= runRandomTests(numRandomTests, EDLIB_MODE_NW, false);
    printf("\n");

    printf("Testing SHW with alignment...\n");
    allTestsPassed &= runRandomTests(numRandomTests, EDLIB_MODE_SHW, true);
    printf("\n");

    printf("Testing SHW...\n");
    allTestsPassed &= runRandomTests(numRandomTests, EDLIB_MODE_SHW, false);
    printf("\n");

    printf("Specific tests:\n");
    bool specificTestsPassed = runTests();
    if (specificTestsPassed)
        printf("All specific tests passed!\n");
    else
        printf("Some specific tests failed\n");
    allTestsPassed &= specificTestsPassed;

    return !allTestsPassed;
}


void fillRandomly(char* seq, int seqLength, int alphabetLength) {
    for (int i = 0; i < seqLength; i++)
        seq[i] = (char) rand() % alphabetLength;
}

// Returns true if all tests passed, false otherwise.
bool runRandomTests(int numTests, EdlibAlignMode mode, bool findAlignment) {
    int alphabetLength = 10;
    int numTestsFailed = 0;
    clock_t start;
    double timeEdlib = 0;
    double timeSimple = 0;

    for (int i = 0; i < numTests; i++) {
        bool failed = false;
        int queryLength = 50 + rand() % 300;
        int targetLength = 500 + rand() % 10000;
        char* query = (char *) malloc(sizeof(char) * queryLength);
        char* target = (char *) malloc(sizeof(char) * targetLength);
        fillRandomly(query, queryLength, alphabetLength);
        fillRandomly(target, targetLength, alphabetLength);

        // // Print query
        // printf("Query: ");
        // for (int i = 0; i < queryLength; i++)
        //     printf("%d", query[i]);
        // printf("\n");

        // // Print target
        // printf("Target: ");
        // for (int i = 0; i < targetLength; i++)
        //     printf("%d", target[i]);
        // printf("\n");

        start = clock();
        EdlibAlignResult result = edlibAlign(
                query, queryLength, target, targetLength,
                edlibNewAlignConfig(-1, mode, findAlignment ? EDLIB_TASK_PATH : EDLIB_TASK_DISTANCE, NULL, 0));
        timeEdlib += clock() - start;
        if (result.alignment) {
            if (!checkAlignment(query, queryLength, target,
                                result.editDistance, result.endLocations[0], mode,
                                result.alignment, result.alignmentLength)) {
                failed = true;
                printf("Alignment is not correct\n");
            }
            int alignmentStart = getAlignmentStart(result.alignment, result.alignmentLength,
                                                   result.endLocations[0]);
            if (result.startLocations[0] != alignmentStart) {
                failed = true;
                printf("Start location (%d) is not consistent with alignment start (%d)\n",
                       result.startLocations[0], alignmentStart);
            }
        }

        start = clock();
        int score2; int numLocations2;
        int* endLocations2;
        calcEditDistanceSimple(query, queryLength, target, targetLength,
                               mode, &score2, &endLocations2, &numLocations2);
        timeSimple += clock() - start;

        // Compare results
        if (result.editDistance != score2) {
            failed = true;
            printf("Scores are different! Expected %d, got %d)\n", score2, result.editDistance);
        } else if (result.editDistance == -1 && !(result.endLocations == NULL)) {
            failed = true;
            printf("Score was not found but endLocations is not NULL!\n");
        } else if (result.numLocations != numLocations2) {
            failed = true;
            printf("Number of endLocations returned is not equal! Expected %d, got %d\n",
                   numLocations2, result.numLocations);
        } else {
            for (int i = 0; i < result.numLocations; i++) {
                if (result.endLocations[i] != endLocations2[i]) {
                    failed = true;
                    printf("EndLocations at %d are not equal! Expected %d, got %d\n",
                           i, endLocations2[i], result.endLocations[i]);
                    break;
                }
            }
        }

        edlibFreeAlignResult(result);
        if (endLocations2) delete [] endLocations2;

        for (int k = max(score2 - 1, 0); k <= score2 + 1; k++) {
            int scoreExpected = score2 > k ? -1 : score2;
            EdlibAlignResult result3 = edlibAlign(
                    query, queryLength, target, targetLength,
                    edlibNewAlignConfig(k, mode, findAlignment ? EDLIB_TASK_PATH : EDLIB_TASK_DISTANCE, NULL, 0));
            if (result3.editDistance != scoreExpected) {
                failed = true;
                printf("For k = %d score was %d but it should have been %d\n",
                       k, result3.editDistance, scoreExpected);
            }
            if (result3.alignment) {
                if (!checkAlignment(query, queryLength, target,
                                    result3.editDistance, result3.endLocations[0],
                                    mode, result3.alignment, result3.alignmentLength)) {
                    failed = true;
                    printf("Alignment is not correct\n");
                }
                int alignmentStart = getAlignmentStart(result3.alignment, result3.alignmentLength,
                                                       result3.endLocations[0]);
                if (result3.startLocations[0] != alignmentStart) {
                    failed = true;
                    printf("Start location (%d) is not consistent with alignment start (%d)\n",
                           result3.startLocations[0], alignmentStart);
                }
            }
            edlibFreeAlignResult(result3);
        }

        if (failed)
            numTestsFailed++;

        free(query);
        free(target);
    }

    printf(mode == EDLIB_MODE_HW ? "HW: " : mode == EDLIB_MODE_SHW ? "SHW: " : "NW: ");
    printf(numTestsFailed == 0 ? "\x1B[32m" : "\x1B[31m");
    printf("%d/%d", numTests - numTestsFailed, numTests);
    printf("\x1B[0m");
    printf(" random tests passed!\n");
    double mTime = ((double)(timeEdlib))/CLOCKS_PER_SEC;
    double sTime = ((double)(timeSimple))/CLOCKS_PER_SEC;
    printf("Time Edlib: %lf\n", mTime);
    printf("Time Simple: %lf\n", sTime);
    printf("Times faster: %.2lf\n", sTime / mTime);
    return numTestsFailed == 0;
}


bool executeTest(const char* query, int queryLength,
                 const char* target, int targetLength,
                 EdlibAlignMode mode) {
    printf(mode == EDLIB_MODE_HW ? "HW:  " : mode == EDLIB_MODE_SHW ? "SHW: " : "NW:  ");

    bool pass = true;

    int scoreSimple; int numLocationsSimple; int* endLocationsSimple;
    calcEditDistanceSimple(query, queryLength, target, targetLength,
                           mode, &scoreSimple, &endLocationsSimple, &numLocationsSimple);

    EdlibAlignResult result = edlibAlign(query, queryLength, target, targetLength,
                                         edlibNewAlignConfig(-1, mode, EDLIB_TASK_PATH, NULL, 0));

    if (result.editDistance != scoreSimple) {
        pass = false;
        printf("Scores: expected %d, got %d\n", scoreSimple, result.editDistance);
    } else if (result.numLocations != numLocationsSimple) {
        pass = false;
        printf("Number of locations: expected %d, got %d\n",
               numLocationsSimple, result.numLocations);
    } else {
        for (int i = 0; i < result.numLocations; i++) {
            if (result.endLocations[i] != endLocationsSimple[i]) {
                pass = false;
                printf("End locations at %d are not equal! Expected %d, got %d\n",
                       i, endLocationsSimple[i], result.endLocations[1]);
                break;
            }
        }
    }
    if (result.alignment) {
        if (!checkAlignment(query, queryLength, target,
                            result.editDistance, result.endLocations[0], mode,
                            result.alignment, result.alignmentLength)) {
            pass = false;
            printf("Alignment is not correct\n");
        }
        int alignmentStart = getAlignmentStart(result.alignment, result.alignmentLength, result.endLocations[0]);
        if (result.startLocations[0] != alignmentStart) {
            pass = false;
            printf("Start location (%d) is not consistent with alignment start (%d)\n",
                   result.startLocations[0], alignmentStart);
        }
    }

    printf(pass ? "\x1B[32m OK \x1B[0m\n" : "\x1B[31m FAIL \x1B[0m\n");

    delete [] endLocationsSimple;
    edlibFreeAlignResult(result);
    return pass;
}

bool test1() {
    int queryLength = 4;
    int targetLength = 4;
    char query[4] = {0,1,2,3};
    char target[4] = {0,1,2,3};

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

bool test2() {
    int queryLength = 5;
    int targetLength = 9;
    char query[5] = {0,1,2,3,4}; // "match"
    char target[9] = {8,5,0,1,3,4,6,7,5}; // "remachine"

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

bool test3() {
    int queryLength = 5;
    int targetLength = 9;
    char query[5] = {0,1,2,3,4};
    char target[9] = {1,2,0,1,2,3,4,5,4};

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

bool test4() {
    int queryLength = 200;
    int targetLength = 200;
    char query[200] = {0};
    char target[200] = {1};

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

bool test5() {
    int queryLength = 64; // Testing for special case when queryLength == word size
    int targetLength = 64;
    char query[64] = {0};
    char target[64] = {1};

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

bool test6() {
    int queryLength = 13; // Testing for special case when queryLength == word size
    int targetLength = 420;
    char query[13] = {1,3,0,1,1,1,3,0,1,3,1,3,3};
    char target[420] = {0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,3,0,1,3,
                        3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,2,3,3,
                        1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,3,0,1,
                        3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,2,3,
                        3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,3,0,
                        1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,2,
                        3,3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,3,
                        0,1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,
                        2,3,3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,
                        3,0,1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,
                        3,2,3,3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,
                        1,3,0,1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,
                        2,3,2,3,3,1,0,1,1,1,0,1,3,0,1,3,3,3,1,3,2,2,3,2,3,3,1,0,1,1,1,
                        0,1,3,0,1,3,3,3,1,3,2,2,3,2,3,3,1};

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

bool test7() {
    int queryLength = 3;
    int targetLength = 5;
    char query[3] = {2,3,0};
    char target[5] = {0,1,2,2,0};

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

bool test8() {
    int queryLength = 3;
    int targetLength = 3;
    char query[3] = {2,3,0};
    char target[3] = {2,2,0};

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

bool test9() {
    int queryLength = 64;
    int targetLength = 393;
    char query[64] = {9,5,5,9,9,4,6,0,1,1,5,4,6,0,6,5,5,6,5,2,2,0,6,0,8,3,7,0,6,6,4,8,3,1,9,4,5,5,5,7,8,2,
                      3,6,4,1,1,2,7,7,6,0,9,2,0,9,6,9,9,4,6,5,2,9};
    char target[393] = {7,1,6,2,9,1,1,7,5,5,4,9,6,7,3,4,6,9,4,5,2,6,6,0,7,8,4,3,3,9,5,2,0,1,7,1,4,0,9,9,7,
                        5,0,6,2,4,0,9,3,6,6,7,4,3,9,3,3,4,7,8,5,4,1,7,7,0,9,3,0,8,4,0,3,4,6,7,0,8,6,6,6,5,
                        5,2,0,5,5,3,1,4,1,6,8,4,3,7,6,2,0,9,0,4,9,5,1,5,3,1,3,1,9,9,6,5,1,8,0,6,1,1,1,5,9,
                        1,1,2,1,8,5,1,7,7,8,6,5,9,1,0,2,4,1,2,5,0,9,6,8,1,4,2,4,5,9,3,9,0,5,0,8,0,3,7,0,1,
                        3,5,0,6,5,5,2,8,9,7,0,8,5,1,9,0,3,3,7,2,6,6,4,3,8,5,6,2,2,6,5,8,3,8,4,0,3,7,8,2,6,
                        9,0,2,0,1,2,5,6,1,9,4,8,3,7,8,8,5,2,3,1,8,1,6,6,7,6,9,6,5,3,3,6,5,7,8,6,1,3,4,2,4,
                        0,0,7,7,1,8,5,3,3,6,1,4,5,7,3,1,8,0,8,1,5,6,6,2,4,4,3,9,8,7,3,8,0,3,8,1,3,3,4,6,1,
                        8,2,6,7,5,8,6,7,8,7,4,5,6,6,9,0,1,1,1,9,4,9,1,9,9,2,2,4,8,0,6,6,4,4,4,2,2,2,9,3,1,
                        6,8,7,2,9,8,6,0,1,7,7,2,8,6,2,2,1,6,0,3,4,9,8,9,3,2,3,5,3,6,6,9,6,6,2,6,6,0,8,7,9,
                        5,9,7,4,3,1,7,2,1,0,6,0,0,7,5,2,1,2,6,9,1,5,6,7};

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

bool test10() {
    int queryLength = 3;
    int targetLength = 3;
    char query[3] = {0,1,2};
    char target[3] = {1,1,1};

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

// Check if edlib works for whole range of char values.
bool test11() {
    int queryLength = 8;
    int targetLength = 8;
    char query[8] =  {-127, 127, -55, 0, 42, 0,      127, -55};
    char target[8] = {-127, 127,      0, 42, 0, -55, 127,  42};

    bool r = executeTest(query, queryLength, target, targetLength, EDLIB_MODE_HW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_NW);
    r = r && executeTest(query, queryLength, target, targetLength, EDLIB_MODE_SHW);
    return r;
}

bool test12() {
    EdlibEqualityPair additionalEqualities[24] = {{'R','A'},{'R','G'},{'M','A'},{'M','C'},{'W','A'},{'W','T'},
                                                  {'S','C'},{'S','G'},{'Y','C'},{'Y','T'},{'K','G'},{'K','T'},
                                                  {'V','A'},{'V','C'},{'V','G'},{'H','A'},{'H','C'},{'H','T'},
                                                  {'D','A'},{'D','G'},{'D','T'},{'B','C'},{'B','G'},{'B','T'}};
    const char* query = "GCATATCAATAAGCGGAGGA";
    const char* target = "TAACAAGGTTTCCGTAGGTGAACCTGCGGAAGGATCATTATCGAATAAACTTGATGGGTTGTCGCTGGCTTCTAGGAGCATGTGCACATCCGTCATTTTTATCCATCCACCTGTGCACCTTTTGTAGTCTTTGGAGGTAATAAGCGTGAATCTATCGAGGTCCTCTGGTCCTCGGAAAGAGGTGTTTGCCATATGGCTCGCCTTTGATACTCGCGAGTTACTCTAAGACTATGTCCTTTCATATACTACGAATGTAATAGAATGTATTCATTGGGCCTCAGTGCCTATAAAACATATACAACTTTCAGCAACGGATCTCTTGGCTCTCGCATCGATGAAGAACGCAGCGAAATGCGATAAGTAATGTGAATTGCAGAATTCAGTGAATCATCGAATCTTTGAACGCACCTTGCGCTCCTTGGTATTCCGAGGAGCATGCCTGTTTGAGTGTCATTAAATTCTCAACCCCTTCCGGTTTTTTGACTGGCTTTGGGGCTTGGATGTGGGGGATTCATTTGCGGGCCTCTGTAGAGGTCGGCTCCCCTGAAATGCATTAGTGGAACCGTTTGCGGTTACCGTCGCTGGTGTGATAACTATCTATGCCAAAGACAAACTGCTCTCTGATAGTTCTGCTTCTAACCGTCCATTTATTGGACAACATTATTATGAACACTTGACCTCAAATCAGGTAGGACTACCCGCTGAACTTAAGCATATCAATAAGCGGAGGAAAAGAAACTAACAAGGATTCCCCTAGTAACTGCGAGTGAAGCGGGAAAAGCTCAAATTTAAAATCTGGCGGTCTTTGGCCGTCCGAGTTGTAATCTAGAGAAGCGACACCCGCGCTGGACCGTGTACAAGTCTCCTGGAATGGAGCGTCATAGAGGGTGAGAATCCCGTCTCTGACACGGACTACCAGGGCTTTGTGGTGCGCTCTCAAAGAGTCGAGTTGTTTGGGAATGCAGCTCTAAATGGGTGGTAAATTCCATCTAAAGCTAAATATTGGCGAGAGACCGATAGCGAACAAGTACCGTGAGGGAAAGATGAAAAGAACTTTGGAAAGAGAGTTAAACAGTACGTGAAATTGCTGAAAGGGAAACGCTTGAAGTCAGTCGCGTTGGCCGGGGATCAGCCTCGCTTTTGCGTGGTGTATTTCCTGGTTGACGGGTCAGCATCAATTTTGACCGCTGGAAAAGGACTTGGGGAATGTGGCATCTTCGGATGTGTTATAGCCCTTTGTCGCATACGGCGGTTGGGATTGAGGAACTCAGCACGCCGCAAGGCCGGGTTTCGACCACGTTCGTGCTTAGGATGCTGGCATAATGGCTTTAATCGACCCGTCTTGAAACACGGACCAAGGAGTCTAACATGCCTGCGAGTGTTTGGGTGGAAAACCCGAGCGCGTAATGAAAGTGAAAGTTGAGATCCCTGTCGTGGGGAGCATCGACGCCCGGACCAGAACTTTTGGGACGGATCTGCGGTAGAGCATGTATGTTGGGACCCGAAAGATGGTGAACTATGCCTGAATAGGGTGAAGCCAGAGGAAACTCTGGTGGAGGCTCGTAGCGATTCTGACGTGCAAATCGATCGTCAAATTTGGGTATAGGGGCGAAAGACTAATCGAACCATCTAGTAGCTGGTTCCTGCCGAAGTTTCCCTCAGGATAGCAGAAACTCATATCAGATTTATGTGGTAAAGCGAATGATTAGAGGCCTTGGGGTTGAAACAACCTTAACCTATTCTCAAACTTTAAATATGTAAGAACGAGCCGTTTCTTGATTGAACCGCTCGGCGATTGAGAGTTTCTAGTGGGCCATTTTTGGTAAGCAGAACTGGCGATGCGGGATGAACCGAACGCGAGGTTAAGGTGCCGGAATTCACGCTCATCAGACACCACAAAAGGTGTTAGTTCATCTAGACAGCAGGACGGTGGCCATGGAAGTCGGAATCCGCTAAGGAGTGTGTAACAACTCACCTGCCGAATGAACTAGCCCTGAAAATGGATGGCGCTTAAGCGTGATACCCATACCTCGCCGTCAGCGTTGAAGTGACGCGCTGACGAGTAGGCAGGCGTGGAGGTCAGTGAAGAAGCCTTGGCAGTGATGCTGGGTGAAACGGCCTCC";

    EdlibAlignResult result = edlibAlign(query, (int) std::strlen(query),
                                         target, (int) std::strlen(target),
                                         edlibNewAlignConfig(-1, EDLIB_MODE_HW,EDLIB_TASK_LOC, additionalEqualities, 24));
    bool pass = result.status == EDLIB_STATUS_OK && result.editDistance == 0;
    printf(pass ? "\x1B[32m""OK""\x1B[0m\n" : "\x1B[31m""FAIL""\x1B[0m\n");
    edlibFreeAlignResult(result);
    return pass;
}

bool testCigar() {
    unsigned char alignment[] = {EDLIB_EDOP_MATCH, EDLIB_EDOP_MATCH, EDLIB_EDOP_INSERT, EDLIB_EDOP_INSERT,
                                 EDLIB_EDOP_INSERT, EDLIB_EDOP_DELETE, EDLIB_EDOP_INSERT, EDLIB_EDOP_INSERT,
                                 EDLIB_EDOP_MISMATCH, EDLIB_EDOP_MATCH, EDLIB_EDOP_MATCH};
    char* cigar = edlibAlignmentToCigar(alignment, 11, EDLIB_CIGAR_EXTENDED);
    bool pass = true;
    char expected[] = "2=3I1D2I1X2=";
    if (strcmp(cigar, expected) != 0) {
        pass = false;
        printf("Expected %s, got %s\n", expected, cigar);
    }
    printf("Cigar extended: ");
    printf(pass ? "\x1B[32m""OK""\x1B[0m\n" : "\x1B[31m""FAIL""\x1B[0m\n");
    if (cigar) free(cigar);

    cigar = edlibAlignmentToCigar(alignment, 11, EDLIB_CIGAR_STANDARD);
    pass = true;
    char expected2[] = "2M3I1D2I3M";
    if (strcmp(cigar, expected2) != 0) {
        pass = false;
        printf("Expected %s, got %s\n", expected2, cigar);
    }
    printf("Cigar standard: ");
    printf(pass ? "\x1B[32m""OK""\x1B[0m\n" : "\x1B[31m""FAIL""\x1B[0m\n");
    if (cigar) free(cigar);

    return pass;
}

bool testCustomEqualityRelation() {
    EdlibEqualityPair additionalEqualities[6] = {{'R','A'},{'R','G'},{'N','A'},{'N','C'},{'N','T'},{'N','G'}};

    bool allPass = true;

    const char* query =  "GTGNRTCARCGAANCTTTN";
    const char* target = "GTGAGTCATCGAATCTTTGAACGCACCTTGCGCTCCTTGGT";

    printf("Degenerate nucleotides (HW): ");
    EdlibAlignResult result = edlibAlign(query, 19, target, 41,
                                         edlibNewAlignConfig(-1, EDLIB_MODE_HW, EDLIB_TASK_PATH,
                                                             additionalEqualities, 6));
    bool pass = result.status == EDLIB_STATUS_OK && result.editDistance == 1;
    edlibFreeAlignResult(result);
    printf(pass ? "\x1B[32m""OK""\x1B[0m\n" : "\x1B[31m""FAIL""\x1B[0m\n");
    allPass = allPass && pass;

    return allPass;
}

bool runTests() {
    // TODO: make this global vector where tests have to add themselves.
    int numTests = 14;
    bool (* tests [])() = {test1, test2, test3, test4, test5, test6,
                           test7, test8, test9, test10, test11, test12, testCigar, testCustomEqualityRelation};

    bool allTestsPassed = true;
    for (int i = 0; i < numTests; i++) {
        printf("Test #%d:\n", i);
        if ( !(*(tests[i]))() ) {
            allTestsPassed = false;
        }
    }
    return allTestsPassed;
}

/**
 * Checks if alignment is correct.
 */
bool checkAlignment(const char* query, int queryLength,
                    const char* target,
                    int score, int pos, EdlibAlignMode mode,
                    unsigned char* alignment, int alignmentLength) {
    int alignScore = 0;
    int qIdx = queryLength - 1;
    int tIdx = pos;
    for (int i = alignmentLength - 1; i >= 0; i--) {
        if (alignment[i] == EDLIB_EDOP_MATCH) { // match
            if (query[qIdx] != target[tIdx]) {
                printf("Should be match but is a mismatch! (tIdx, qIdx, i): (%d, %d, %d)\n", tIdx, qIdx, i);
                return false;
            }
            qIdx--;
            tIdx--;
        } else if (alignment[i] == EDLIB_EDOP_MISMATCH) { // mismatch
            if (query[qIdx] == target[tIdx]) {
                printf("Should be mismatch but is a match! (tIdx, qIdx, i): (%d, %d, %d)\n", tIdx, qIdx, i);
                return false;
            }
            alignScore += 1;
            qIdx--;
            tIdx--;
        } else if (alignment[i] == EDLIB_EDOP_INSERT) {
            alignScore += 1;
            qIdx--;
        } else if (alignment[i] == EDLIB_EDOP_DELETE) {
            if (!(mode == EDLIB_MODE_HW && qIdx == -1))
                alignScore += 1;
            tIdx--;
        }
        if (tIdx < -1 || qIdx < -1) {
            printf("Alignment went outside of matrix! (tIdx, qIdx, i): (%d, %d, %d)\n", tIdx, qIdx, i);
            return false;
        }
    }
    if (qIdx != -1) {
        printf("Alignment did not reach end!\n");
        return false;
    }
    if (alignScore != score) {
        printf("Wrong score in alignment! %d should be %d\n", alignScore, score);
        return false;
    }
    if (alignmentLength > 0 && alignment[0] == EDLIB_EDOP_INSERT && tIdx >= 0) {
        printf("Alignment starts with insertion in target, while it could start with mismatch!\n");
        return false;
    }
    return true;
}

/**
 * @param alignment
 * @param alignmentLength
 * @param endLocation
 * @return Return start location of alignment in target, if there is none return -1.
 */
int getAlignmentStart(const unsigned char* alignment, int alignmentLength,
                      int endLocation) {
    int startLocation = endLocation + 1;
    for (int i = 0; i < alignmentLength; i++) {
        if (alignment[i] != EDLIB_EDOP_INSERT) {
            startLocation--;
        }
    }
    if (startLocation > endLocation) {
        return -1;
    }
    return startLocation;
}
