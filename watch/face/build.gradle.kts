// The Claude watch face, in Watch Face Format: resources only, no code. Its images and
// res/raw/watchface.xml are written by tools/face.py. See README.md.
plugins {
    id("com.android.application")
}

android {
    namespace = "io.github.mikalio.claudewatch.face"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.mikalio.claudewatch.face"
        // Watch Face Format version 2 needs Wear OS 5 (API 34)
        minSdk = 34
        targetSdk = 34
        versionCode = 1
        versionName = "0.1"
    }

    signingConfigs {
        // The same shared debug key as the app, so builds from GitHub install over each other
        getByName("debug") {
            storeFile = file("../debug.keystore")
            storeType = "pkcs12"
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }
}
