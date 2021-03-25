all: system_metrics system_metrics.so


system_metrics.so: system_metrics.c
	gcc -shared -fPIC -o $@ $^

system_metrics: system_metrics.c
	gcc -o $@ -DINTERACTIVE $^
