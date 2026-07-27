// main.c
// Command-line helper to control the fans of an
// Intel MacBook Pro via the SMC. Intended to be invoked by
// a graphical interface (see fan_control_gui.py), but it also works standalone
// from the terminal.
//
// Usage:
//   smc-helper info
//       Lists each fan: index, actual RPM, minimum, maximum, mode
//
//   smc-helper set <index> <rpm>
//       Forces manual mode on that fan and sets the target RPM
//
//   smc-helper auto
//       Returns ALL fans to macOS automatic control
//
// IMPORTANT: writing to the SMC requires administrator privileges.
// Run this binary with sudo, or let the GUI ask for the password.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "smc.h"

static void printUsage(const char *prog)
{
    fprintf(stderr,
        "Usage:\n"
        "  %s info\n"
        "  %s set <fan_index> <rpm>\n"
        "  %s auto\n",
        prog, prog, prog);
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        printUsage(argv[0]);
        return 1;
    }

    io_connect_t conn;
    if (SMCOpen(&conn) != KERN_SUCCESS) {
        fprintf(stderr, "ERROR: could not open connection to the SMC.\n");
        return 1;
    }

    int exitCode = 0;

    if (strcmp(argv[1], "info") == 0) {
        int count = SMCGetFanCount(conn);
        if (count < 0) {
            fprintf(stderr, "ERROR: could not read the number of fans.\n");
            exitCode = 1;
        } else {
            UInt16 manualMask = 0;
            SMCGetManualMode(conn, &manualMask);

            // Temperatures
            double cpu = SMCGetTemperature(conn, "TC0P");
            double gpu = SMCGetTemperature(conn, "TG0P");
            printf("TEMP_CPU=%.1f\n", cpu);
            printf("TEMP_GPU=%.1f\n", gpu);

            printf("FAN_COUNT=%d\n", count);
            for (int i = 0; i < count; i++) {
                double actual = SMCGetFanRPM(conn, i, "Ac");
                double minRpm = SMCGetFanRPM(conn, i, "Mn");
                double maxRpm = SMCGetFanRPM(conn, i, "Mx");
                double target = SMCGetFanRPM(conn, i, "Tg");
                int isManual = (manualMask & (1 << i)) != 0;
                printf("FAN=%d ACTUAL=%.0f MIN=%.0f MAX=%.0f TARGET=%.0f MODE=%s\n",
                    i, actual, minRpm, maxRpm, target,
                    isManual ? "MANUAL" : "AUTO");
            }
        }
    }
    else if (strcmp(argv[1], "set") == 0) {
        if (argc < 4) {
            printUsage(argv[0]);
            exitCode = 1;
        } else {
            int fanIndex = atoi(argv[2]);
            double rpm = atof(argv[3]);

            kern_return_t r1 = SMCSetFanManual(conn, fanIndex, 1);
            kern_return_t r2 = SMCSetFanTargetRPM(conn, fanIndex, rpm);

            if (r2 == KERN_SUCCESS) {
                printf("OK fan=%d target=%.0f\n", fanIndex, rpm);
            } else {
                fprintf(stderr, "ERROR: could not set speed (r1=%d r2=%d)\n", (int)r1, (int)r2);
                exitCode = 1;
            }
        }
    }
    else if (strcmp(argv[1], "auto") == 0) {
        int count = SMCGetFanCount(conn);
        int ok = 1;
        for (int i = 0; i < count && i < 8; i++) {
            if (SMCSetFanManual(conn, i, 0) != KERN_SUCCESS)
                ok = 0;
        }
        if (ok) printf("OK automatic mode restored\n");
        else {
            fprintf(stderr, "ERROR: could not restore automatic mode\n");
            exitCode = 1;
        }
    }
    else {
        printUsage(argv[0]);
        exitCode = 1;
    }

    SMCClose(conn);
    return exitCode;
}