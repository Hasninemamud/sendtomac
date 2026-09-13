#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    char exe[4096];
    uint32_t size = sizeof(exe);
    if (_NSGetExecutablePath(exe, &size) != 0) return 1;
    char *slash = strrchr(exe, '/');
    if (!slash) return 1;
    *slash = 0;
    char bin[4096];
#if defined(__x86_64__)
    const char *which = "Intel";
#else
    const char *which = "AppleSilicon";
#endif
    snprintf(bin, sizeof(bin), "%s/../Resources/%s/SendToMac.app/Contents/MacOS/SendToMac", exe, which);
    argv[0] = bin;
    execv(bin, argv);
    fprintf(stderr, "Could not start SendToMac\n");
    return 1;
}
