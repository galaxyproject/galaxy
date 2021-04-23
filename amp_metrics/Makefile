all: system_metrics system_metrics.so


system_metrics.so: system_metrics.c
	gcc -std=gnu99 -shared -fPIC -o $@ $^

system_metrics: system_metrics.c
	gcc -std=gnu99 -o $@ -DINTERACTIVE $^


clean:
	rm system_metrics system_metrics.so
