// Swift-facing wrapper around nuqta_core (llama.cpp + mtmd, Metal)
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface NuqtaEngine : NSObject

/// Loads the model and its vision file. Returns nil on success, or an error message.
+ (nullable NSString *)loadModel:(NSString *)modelPath mmproj:(NSString *)mmprojPath threads:(int)threads;

/// Reads an RGB image (w*h*3 bytes). Blocks until done; call it off the main thread.
/// onText returns NO to stop. Returns nil on success, or an error message.
+ (nullable NSString *)readRGB:(NSData *)rgb
                         width:(int)width
                        height:(int)height
                        prompt:(NSString *)prompt
                       onStage:(void (^)(int stage))onStage
                        onText:(BOOL (^)(NSString *piece))onText
                        onDone:(void (^)(int outTokens, double firstSeconds, double genSeconds))onDone;

@end

NS_ASSUME_NONNULL_END
