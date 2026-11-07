plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.gms.google-services")
}

android {
    namespace = "io.github.mikalio.claudewatch"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.mikalio.claudewatch"
        minSdk = 30 // Wear OS 3, the oldest the Galaxy Watch 4 shipped with
        targetSdk = 34
        versionCode = 1
        versionName = "0.1"
        // The relay sends to this Firebase topic: the same value as FCM_TOPIC on your relay (see gradle.properties)
        buildConfigField("String", "FCM_TOPIC", "\"${project.findProperty("claudeWatchTopic")}\"")
    }

    signingConfigs {
        // One shared debug key in the repo, so builds from GitHub install over each other
        getByName("debug") {
            storeFile = file("../debug.keystore")
            storeType = "pkcs12"
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(platform("com.google.firebase:firebase-bom:33.7.0"))
    implementation("com.google.firebase:firebase-messaging")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.wear.tiles:tiles:1.4.1")
    implementation("androidx.wear.protolayout:protolayout:1.2.1")
    implementation("androidx.wear.protolayout:protolayout-expression:1.2.1")
    implementation("androidx.wear.watchface:watchface-complications-data-source-ktx:1.2.1")
    implementation("com.google.guava:guava:33.3.1-android")
}
