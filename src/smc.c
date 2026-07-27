#include "smc.h"
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <IOKit/IOKitLib.h>

static kern_return_t SMCCall(io_connect_t conn, int index,
                             SMCParamStruct *in, SMCParamStruct *out)
{
    size_t inSize = sizeof(SMCParamStruct);
    size_t outSize = sizeof(SMCParamStruct);
    return IOConnectCallStructMethod(conn, index, in, inSize, out, &outSize);
}

kern_return_t SMCOpen(io_connect_t *conn)
{
    io_service_t service = IOServiceGetMatchingService(kIOMainPortDefault,
                            IOServiceMatching("AppleSMC"));
    if (service == 0)
        service = IOServiceGetMatchingService(kIOMasterPortDefault,
                            IOServiceMatching("AppleSMC"));
    if (service == 0) {
        fprintf(stderr, "AppleSMC not found\n");
        return KERN_FAILURE;
    }
    kern_return_t result = IOServiceOpen(service, mach_task_self(), 0, conn);
    IOObjectRelease(service);
    return result;
}

kern_return_t SMCClose(io_connect_t conn) {
    return IOServiceClose(conn);
}

static UInt32 strToKey(const char *key) {
    UInt32 result = 0;
    for (int i = 0; i < 4 && key[i]; i++)
        result = (result << 8) | (UInt8)key[i];
    return result;
}

static void keyToStr(UInt32 key, char *out) {
    out[0] = (key >> 24) & 0xFF;
    out[1] = (key >> 16) & 0xFF;
    out[2] = (key >> 8)  & 0xFF;
    out[3] =  key        & 0xFF;
    out[4] = '\0';
}

kern_return_t SMCReadKey(io_connect_t conn, const char *key, SMCVal_t *val)
{
    SMCParamStruct in, out;
    memset(&in, 0, sizeof(in));
    memset(&out, 0, sizeof(out));
    memset(val, 0, sizeof(*val));
    strncpy(val->key, key, 4);

    in.key = strToKey(key);
    in.data8 = kSMCGetKeyInfo;
    kern_return_t r = SMCCall(conn, kSMCHandleYPCEvent, &in, &out);
    if (r != KERN_SUCCESS || out.result != 0)
        return r != KERN_SUCCESS ? r : KERN_FAILURE;

    val->dataSize = out.keyInfo.dataSize;
    keyToStr(out.keyInfo.dataType, val->dataType);

    memset(&in, 0, sizeof(in));
    in.key = strToKey(key);
    in.keyInfo.dataSize = val->dataSize;
    in.data8 = kSMCReadKey;
    memset(&out, 0, sizeof(out));
    r = SMCCall(conn, kSMCHandleYPCEvent, &in, &out);
    if (r != KERN_SUCCESS || out.result != 0)
        return r != KERN_SUCCESS ? r : KERN_FAILURE;

    memcpy(val->bytes, out.bytes, sizeof(val->bytes));
    return KERN_SUCCESS;
}

kern_return_t SMCWriteKey(io_connect_t conn, SMCVal_t val)
{
    SMCVal_t current;
    if (SMCReadKey(conn, val.key, &current) != KERN_SUCCESS)
        return KERN_FAILURE;

    SMCParamStruct in, out;
    memset(&in, 0, sizeof(in));
    memset(&out, 0, sizeof(out));
    in.key = strToKey(val.key);
    in.data8 = kSMCWriteKey;
    in.keyInfo.dataSize = current.dataSize;
    memcpy(in.bytes, val.bytes, sizeof(in.bytes));

    kern_return_t r = SMCCall(conn, kSMCHandleYPCEvent, &in, &out);
    if (r != KERN_SUCCESS) return r;
    if (out.result != 0) return KERN_FAILURE;
    return KERN_SUCCESS;
}

// ---- Decoders ----
static float bytesToFloat(const SMCBytes_t b) {
    float f; memcpy(&f, b, 4); return f;
}
static void floatToBytes(float v, SMCBytes_t out) {
    memcpy(out, &v, 4);
}
static double fpe2ToDouble(const SMCBytes_t b) {
    UInt16 raw = ((UInt8)b[0] << 8) | (UInt8)b[1];
    return raw / 4.0;
}
static void doubleToFpe2(double v, SMCBytes_t out) {
    UInt16 raw = (UInt16)(v * 4.0 + 0.5);
    out[0] = (raw >> 8) & 0xFF;
    out[1] = raw & 0xFF;
}
static double sp78ToDouble(const SMCBytes_t b) {
    int16_t raw = (int16_t)(((UInt8)b[0] << 8) | (UInt8)b[1]);
    return raw / 256.0;
}

int SMCGetFanCount(io_connect_t conn) {
    SMCVal_t val;
    if (SMCReadKey(conn, "FNum", &val) != KERN_SUCCESS) return -1;
    return (int)(UInt8)val.bytes[0];
}

double SMCGetFanRPM(io_connect_t conn, int fanIndex, const char *suffix) {
    char key[5];
    snprintf(key, sizeof(key), "F%d%s", fanIndex, suffix);
    SMCVal_t val;
    if (SMCReadKey(conn, key, &val) != KERN_SUCCESS) return -1.0;

    if (strncmp(val.dataType, "flt", 3) == 0 && val.dataSize == 4)
        return (double)bytesToFloat(val.bytes);
    if (strncmp(val.dataType, "fpe2", 4) == 0)
        return fpe2ToDouble(val.bytes);
    return fpe2ToDouble(val.bytes);
}

kern_return_t SMCSetFanTargetRPM(io_connect_t conn, int fanIndex, double rpm) {
    char key[5];
    snprintf(key, sizeof(key), "F%dTg", fanIndex);
    SMCVal_t current;
    if (SMCReadKey(conn, key, &current) != KERN_SUCCESS)
        return KERN_FAILURE;

    SMCVal_t val = {0};
    strncpy(val.key, key, 4);
    val.dataSize = current.dataSize;
    strncpy(val.dataType, current.dataType, 4);

    if (strncmp(current.dataType, "flt", 3) == 0)
        floatToBytes((float)rpm, val.bytes);
    else
        doubleToFpe2(rpm, val.bytes);

    return SMCWriteKey(conn, val);
}

kern_return_t SMCSetFanManual(io_connect_t conn, int fanIndex, int manual) {
    char key[5];
    snprintf(key, sizeof(key), "F%dMd", fanIndex);
    SMCVal_t val = {0};
    strncpy(val.key, key, 4);
    strncpy(val.dataType, "ui8 ", 4);
    val.dataSize = 1;
    val.bytes[0] = manual ? 1 : 0;
    return SMCWriteKey(conn, val);
}

kern_return_t SMCGetFanManual(io_connect_t conn, int fanIndex, int *manual) {
    char key[5];
    snprintf(key, sizeof(key), "F%dMd", fanIndex);
    SMCVal_t val;
    if (SMCReadKey(conn, key, &val) != KERN_SUCCESS) return KERN_FAILURE;
    *manual = (val.bytes[0] != 0);
    return KERN_SUCCESS;
}

kern_return_t SMCSetManualMode(io_connect_t conn, UInt16 bitmask) {
    for (int i = 0; i < 8; i++)
        SMCSetFanManual(conn, i, (bitmask & (1 << i)) != 0);
    return KERN_SUCCESS;
}

kern_return_t SMCGetManualMode(io_connect_t conn, UInt16 *bitmask) {
    *bitmask = 0;
    for (int i = 0; i < 2; i++) {
        int man = 0;
        if (SMCGetFanManual(conn, i, &man) == KERN_SUCCESS && man)
            *bitmask |= (1 << i);
    }
    return KERN_SUCCESS;
}

double SMCGetTemperature(io_connect_t conn, const char *key) {
    SMCVal_t val;
    if (SMCReadKey(conn, key, &val) != KERN_SUCCESS) return -1.0;

    if (strncmp(val.dataType, "sp78", 4) == 0)
        return sp78ToDouble(val.bytes);
    if (strncmp(val.dataType, "flt", 3) == 0 && val.dataSize == 4)
        return (double)bytesToFloat(val.bytes);
    return -1.0;
}