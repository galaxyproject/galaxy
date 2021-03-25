#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/sysinfo.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

/* minimum time (in milliseconds) allowed between CPU Stat updates */
#define MIN_STAT_FREQ 500
#define STAT_COUNT 7 /* # of stat values in /proc/stat */
//#define DEBUG

/* Get the system load average */
int64_t load_average(void *metric) {
    double avg[3];
    getloadavg(avg, 3);
    return (int64_t)(avg[0] * 100.0);
}

/* get % system memory used */
int64_t memory(void *metric) {
    FILE *f = fopen("/proc/meminfo", "r");
    if(!f) return 999;
    char buffer[256];
    float total = 0;
    float available = 0;
    while(fgets(buffer, sizeof(buffer), f)) {
        sscanf(buffer, "MemTotal: %f kB", &total);
        if(sscanf(buffer, "MemAvailable: %f kB", &available) == 1) {
            break;
        }
    }
    fclose(f);
#ifdef DEBUG
    printf("Meminfo: Total: %f, Available: %f\n", total, available);
#endif
    return (int64_t)(100 * available / total);
}

/* Get the % of swap that's used */
int64_t swap(void *metric) {
    struct sysinfo si;
    sysinfo(&si);
    if(si.totalswap) {
        return (int64_t)(100.0 * si.freeswap / si.totalswap);
    } else {
        return 0;
    }
}

/* CPU Stats are harder:  they're a time-based computation so we have
   to compute the delta percentages, otherwise we just get percentages
   over the entire uptime */
int64_t get_mstime() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return ((int64_t)tv.tv_sec * 1000) + tv.tv_usec / 1000;
}

int64_t get_cpu_stat(int col) {
    // static storage
    static int64_t last_update = 0;
    static float previous[STAT_COUNT] = {0.0};
    static int64_t cached[STAT_COUNT] = {0};

    int64_t now = get_mstime();
    // fast path:  if it's too soon just give back the cache.
    if(last_update && (now - last_update < MIN_STAT_FREQ)) {
#ifdef DEBUG        
        printf("FAST PATH %d = %d\n", col, cached[col]);
#endif
        return cached[col];
    }

    char buffer[256];
    float new[STAT_COUNT] = {0.0};
    FILE *s = fopen("/proc/stat", "r");
    if(s == NULL) return 999;
    fgets(buffer, sizeof(buffer), s);
    fclose(s);

    char *saveptr = NULL;
    char *token = strtok_r(buffer + 4, " ", &saveptr); // skip "cpu "
    for(int i = 0; i < STAT_COUNT && token; i++) {
        new[i] = strtof(token, NULL);
        token = strtok_r(NULL, " ", &saveptr);
#ifdef DEBUG
        printf("(new) /proc/stat field %d: %f\n", i, new[i]);
#endif
    }

    if(last_update == 0) {
        // special case to seed the values with something reasonable
        // fill in our values, wait 1/2 second and then call ourselves.
        for(int i = 0; i < STAT_COUNT; i++) 
            previous[i] = new[i];
        last_update = now;
        usleep((MIN_STAT_FREQ + 1) * 1000); 
#ifdef DEBUG
        printf("Calling ourselves because we're new here\n");
#endif
        return get_cpu_stat(col);
    }

    float deltavals[STAT_COUNT] = {0.0};
    uint64_t update_delta = now - last_update;
    float total;
    for(int i = 0; i < STAT_COUNT; i++) {
        deltavals[i] = new[i] - previous[i];
        total += deltavals[i];
#ifdef DEBUG
        printf("(delta) %d:  %f - %f = %f; total=%f\n", i, new[i], previous[i], deltavals[i], total);
#endif
        previous[i] = new[i];
    }
    for(int i = 0; i < STAT_COUNT; i++) {
        cached[i] = (100.0 * deltavals[i]) / total;
#ifdef DEBUG
        printf("(cached)%d: %d\n", i, cached[i]);
#endif
    }
    last_update = now;
    return cached[col];
}

#define gen_stat_func(func, column) \
    int64_t func(void *metric) { \
        return get_cpu_stat(column); \
    } \

gen_stat_func(cpu_user, 0)
gen_stat_func(cpu_system, 2)
gen_stat_func(cpu_idle, 3)
gen_stat_func(cpu_iowait, 4)

#ifdef INTERACTIVE
int main(int argc, char **argv) {
    struct sysinfo si;
    sysinfo(&si);
    printf("MEMORY STAT: %d\n", memory(NULL));
    printf("SWAP STAT: %d\n", swap(NULL));
    for(int j = 0; j < 20; j++) {
        printf("Gen funcs: user=%d, sys=%d, idle=%d, iowait=%d\n", cpu_user(NULL), cpu_system(NULL), cpu_idle(NULL), cpu_iowait(NULL));
        usleep(1000 * 1000);
    }
}
#endif