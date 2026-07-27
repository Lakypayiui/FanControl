#ifndef SMC_H
#define SMC_H

#include <IOKit/IOKitLib.h>

#ifdef __cplusplus
extern "C" {
#endif

#define KERNEL_INDEX_SMC 2

typedef enum {
    kSMCUserClientOpen  = 0,
    kSMCUserClientClose = 1,
    kSMCHandleYPCEvent  = 2,
    kSMCReadKey         = 5,
    kSMCWriteKey        = 6,
    kSMCGetKeyCount     = 7,
    kSMCGetKeyFromIndex = 8,
    kSMCGetKeyInfo      = 9,
} smc_selector_t;

typedef struct {
    char major, minor, build, reserved;
    UInt16 release;
} SMCVersion;

typedef struct {
    UInt16 version, length;
    UInt32 cpuPLimit, gpuPLimit, memPLimit;
} SMCPLimitData;

typedef struct {
    UInt32 dataSize;
    UInt32 dataType;
    char dataAttributes;
} SMCKeyInfo;

typedef char SMCBytes_t[32];

typedef struct {
    UInt32 key;
    SMCVersion vers;
    SMCPLimitData pLimitData;
    SMCKeyInfo keyInfo;
    char result;
    char status;
    char data8;
    UInt32 data32;
    SMCBytes_t bytes;
} SMCParamStruct;

typedef struct {
    char key[5];
    UInt32 dataSize;
    char dataType[5];
    SMCBytes_t bytes;
} SMCVal_t;

kern_return_t SMCOpen(io_connect_t *conn);
kern_return_t SMCClose(io_connect_t conn);
kern_return_t SMCReadKey(io_connect_t conn, const char *key, SMCVal_t *val);
kern_return_t SMCWriteKey(io_connect_t conn, SMCVal_t val);

int     SMCGetFanCount(io_connect_t conn);
double  SMCGetFanRPM(io_connect_t conn, int fanIndex, const char *suffix);
kern_return_t SMCSetFanTargetRPM(io_connect_t conn, int fanIndex, double rpm);
kern_return_t SMCSetFanManual(io_connect_t conn, int fanIndex, int manual);
kern_return_t SMCGetFanManual(io_connect_t conn, int fanIndex, int *manual);
kern_return_t SMCSetManualMode(io_connect_t conn, UInt16 bitmask);
kern_return_t SMCGetManualMode(io_connect_t conn, UInt16 *bitmask);

// Temperaturas
double SMCGetTemperature(io_connect_t conn, const char *key);

#ifdef __cplusplus
}
#endif
#endif