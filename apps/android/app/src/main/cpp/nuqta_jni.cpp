// JNI bridge for ai.nuqta.ocr.Engine
#include <jni.h>
#include <android/log.h>
#include <string>

#include "llama.h"
#include "nuqta_core.h"

static void android_log(ggml_log_level level, const char * text, void *) {
    if (level >= GGML_LOG_LEVEL_WARN) __android_log_print(ANDROID_LOG_WARN, "nuqta", "%s", text);
}

static std::string str(JNIEnv * env, jstring s) {
    const char * c = env->GetStringUTFChars(s, nullptr);
    std::string out(c);
    env->ReleaseStringUTFChars(s, c);
    return out;
}

// Java strings are modified UTF-8; build them from raw UTF-8 bytes instead
static jstring jstr(JNIEnv * env, const std::string & s) {
    jbyteArray bytes = env->NewByteArray((jsize) s.size());
    env->SetByteArrayRegion(bytes, 0, (jsize) s.size(), (const jbyte *) s.data());
    jclass strCls = env->FindClass("java/lang/String");
    jmethodID ctor = env->GetMethodID(strCls, "<init>", "([BLjava/lang/String;)V");
    jstring enc = env->NewStringUTF("UTF-8");
    auto out = (jstring) env->NewObject(strCls, ctor, bytes, enc);
    env->DeleteLocalRef(bytes);
    env->DeleteLocalRef(enc);
    env->DeleteLocalRef(strCls);
    return out;
}

extern "C" JNIEXPORT jstring JNICALL
Java_ai_nuqta_ocr_Engine_nativeLoad(JNIEnv * env, jobject, jstring model, jstring mmproj, jint threads, jint maxImageTokens,
                                    jstring libDir) {
    llama_log_set(android_log, nullptr);
    std::string err;
    if (!nuqta::load(str(env, model), str(env, mmproj), threads, maxImageTokens, str(env, libDir), err)) return jstr(env, err);
    return nullptr;
}

extern "C" JNIEXPORT jstring JNICALL
Java_ai_nuqta_ocr_Engine_nativeRead(JNIEnv * env, jobject, jbyteArray rgb, jint w, jint h, jstring prompt, jint maxTokens,
                                    jobject listener) {
    jclass cls = env->GetObjectClass(listener);
    jmethodID onStage = env->GetMethodID(cls, "onStage", "(I)V");
    jmethodID onText = env->GetMethodID(cls, "onText", "(Ljava/lang/String;)Z");
    jmethodID onDone = env->GetMethodID(cls, "onDone", "(IIDD)V");

    jbyte * px = env->GetByteArrayElements(rgb, nullptr);
    nuqta::Stats st;
    std::string err;
    bool ok = nuqta::read((const uint8_t *) px, w, h, str(env, prompt), maxTokens, true,
        [&](int s) { env->CallVoidMethod(listener, onStage, s); },
        [&](const std::string & t) {
            jstring js = jstr(env, t);
            jboolean go = env->CallBooleanMethod(listener, onText, js);
            env->DeleteLocalRef(js);
            return (bool) go;
        }, st, err);
    env->ReleaseByteArrayElements(rgb, px, JNI_ABORT);
    env->CallVoidMethod(listener, onDone, st.image_tokens, st.out_tokens, st.encode_s, st.gen_s);
    return ok ? nullptr : jstr(env, err);
}
