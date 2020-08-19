#ifndef SIMPLE_EDIT_DISTANCE_H
#define SIMPLE_EDIT_DISTANCE_H

#include <cstdio>
#include <vector>
#include "edlib.h"

using namespace std;

#ifdef __cplusplus
extern "C" {
#endif


int min(int x, int y) {
    return x < y ? x : y;
}

int min3(int x, int y, int z) {
    return min(x, min(y, z));
}

int calcEditDistanceSimple(const char* query, int queryLength,
                           const char* target, int targetLength,
                           EdlibAlignMode mode, int* score,
                           int** positions_, int* numPositions_) {
    int* C = new int[queryLength];
    int* newC = new int[queryLength];

    int bestScore = -1;
    vector<int> positions;
    int numPositions = 0;

    // set first column (column zero)
    for (int i = 0; i < queryLength; i++) {
        C[i] = i + 1;
    }
    /*
    for (int i = 0; i < queryLength; i++)
        printf("%3d ", C[i]);
    printf("\n");
    */
    for (int c = 0; c < targetLength; c++) { // for each column
        newC[0] = min3((mode == EDLIB_MODE_HW ? 0 : c + 1) + 1, // up
                       (mode == EDLIB_MODE_HW ? 0 : c)
                       + (target[c] == query[0] ? 0 : 1), // up left
                       C[0] + 1); // left
        for (int r = 1; r < queryLength; r++) {
            newC[r] = min3(newC[r-1] + 1, // up
                           C[r-1] + (target[c] == query[r] ? 0 : 1), // up left
                           C[r] + 1); // left
        }

        /*  for (int i = 0; i < queryLength; i++)
            printf("%3d ", newC[i]);
            printf("\n");*/

        if (mode != EDLIB_MODE_NW || c == targetLength - 1) { // For NW check only last column
            int score = newC[queryLength - 1];
            if (bestScore == -1 || score <= bestScore) {
                if (score < bestScore) {
                    positions.clear();
                    numPositions = 0;
                }
                bestScore = score;
                positions.push_back(c);
                numPositions++;
            }
        }

        int *tmp = C;
        C = newC;
        newC = tmp;
    }

    delete[] C;
    delete[] newC;

    *score = bestScore;
    if (positions.size() > 0) {
        *positions_ = new int[positions.size()];
        *numPositions_ = (int) positions.size();
        copy(positions.begin(), positions.end(), *positions_);
    } else {
        *positions_ = NULL;
        *numPositions_ = 0;
    }

    return EDLIB_STATUS_OK;
}



#ifdef __cplusplus
}
#endif

#endif // SIMPLE_EDIT_DISTANCE_H
