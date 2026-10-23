#import "NuqtaEngine.h"
#include "nuqta_core.h"

@implementation NuqtaEngine

+ (NSString *)loadModel:(NSString *)modelPath mmproj:(NSString *)mmprojPath threads:(int)threads {
    std::string err;
    if (!nuqta::load(modelPath.UTF8String, mmprojPath.UTF8String, threads, 4096, "", err)) {
        return [NSString stringWithUTF8String:err.c_str()];
    }
    return nil;
}

+ (NSString *)readRGB:(NSData *)rgb width:(int)width height:(int)height prompt:(NSString *)prompt
              onStage:(void (^)(int))onStage onText:(BOOL (^)(NSString *))onText
               onDone:(void (^)(int, double, double))onDone {
    nuqta::Stats st;
    std::string err;
    bool ok = nuqta::read((const uint8_t *) rgb.bytes, width, height, prompt.UTF8String, 4096, true,
        [&](int s) { onStage(s); },
        [&](const std::string & t) {
            NSString * piece = [[NSString alloc] initWithBytes:t.data() length:t.size() encoding:NSUTF8StringEncoding];
            return (bool) onText(piece ?: @"");
        }, st, err);
    onDone(st.out_tokens, st.first_s, st.gen_s);
    return ok ? nil : [NSString stringWithUTF8String:err.c_str()];
}

@end
