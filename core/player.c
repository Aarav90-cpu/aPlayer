#define MINIAUDIO_IMPLEMENTATION
#include "miniaudio.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

ma_engine engine;
ma_sound current_sound;
bool is_initialized = false;
bool sound_playing = false;
float current_volume = 1.0f; // 100%
bool spatializer_enabled = false;
ma_context context;
bool context_initialized = false;

void player_init() {
    if (!is_initialized) {
        ma_backend backends[] = { ma_backend_alsa };
        if (ma_context_init(backends, 1, NULL, &context) == MA_SUCCESS) {
            context_initialized = true;
        }

        ma_engine_config engineConfig = ma_engine_config_init();
        if (context_initialized) {
            engineConfig.pContext = &context;
            
            ma_device_info* pPlaybackInfos;
            ma_uint32 playbackCount;
            if (ma_context_get_devices(&context, &pPlaybackInfos, &playbackCount, NULL, NULL) == MA_SUCCESS) {
                for (ma_uint32 i = 0; i < playbackCount; i++) {
                    if (strstr(pPlaybackInfos[i].name, "sof-hda-dsp") != NULL || strstr(pPlaybackInfos[i].name, "hw:") != NULL) {
                        engineConfig.pPlaybackDeviceID = &pPlaybackInfos[i].id;
                        printf("aPlayer: ALSA hardware device engaged: %s\n", pPlaybackInfos[i].name);
                        break;
                    }
                }
            }
        }

        if (ma_engine_init(&engineConfig, &engine) != MA_SUCCESS) {
            printf("Failed to initialize miniaudio engine.\n");
            return;
        }
        is_initialized = true;
    }
}

void player_play(const char *filepath) {
    if (!is_initialized) return;

    if (sound_playing) {
        ma_sound_uninit(&current_sound);
        sound_playing = false;
    }

    // Initialize the sound for streaming
    if (ma_sound_init_from_file(&engine, filepath, MA_SOUND_FLAG_STREAM, NULL, NULL, &current_sound) != MA_SUCCESS) {
        printf("Failed to load sound file: %s\n", filepath);
        return;
    }
    
    // Apply spatializer and volume settings to new sound
    if (spatializer_enabled) {
        ma_sound_set_spatialization_enabled(&current_sound, MA_TRUE);
        ma_engine_listener_set_position(&engine, 0, 0.0f, 0.0f, 0.0f);
        ma_sound_set_position(&current_sound, 0.0f, 0.0f, -1.0f); 
    } else {
        ma_sound_set_spatialization_enabled(&current_sound, MA_FALSE);
    }
    
    ma_sound_set_volume(&current_sound, current_volume);
    
    ma_sound_start(&current_sound);
    sound_playing = true;
}

void player_pause() {
    if (sound_playing && ma_sound_is_playing(&current_sound)) {
        ma_sound_stop(&current_sound);
    } else if (sound_playing) {
        ma_sound_start(&current_sound);
    }
}

void player_stop() {
    if (sound_playing) {
        ma_sound_stop(&current_sound);
        ma_sound_seek_to_pcm_frame(&current_sound, 0);
    }
}

int player_is_playing() {
    if (sound_playing && ma_sound_is_playing(&current_sound)) {
        return 1;
    }
    return 0;
}

float player_get_position() {
    if (sound_playing) {
        ma_uint64 cursor;
        ma_uint64 length;
        ma_sound_get_cursor_in_pcm_frames(&current_sound, &cursor);
        ma_sound_get_length_in_pcm_frames(&current_sound, &length);
        if (length > 0) {
            return (float)cursor / (float)length;
        }
    }
    return 0.0f;
}

void player_set_position(float pos) {
    if (sound_playing) {
        ma_uint64 length;
        ma_sound_get_length_in_pcm_frames(&current_sound, &length);
        ma_sound_seek_to_pcm_frame(&current_sound, (ma_uint64)(pos * length));
    }
}

long long player_get_length() {
    if (sound_playing) {
        ma_uint64 length;
        ma_uint32 sampleRate;
        ma_sound_get_length_in_pcm_frames(&current_sound, &length);
        ma_sound_get_data_format(&current_sound, NULL, NULL, &sampleRate, NULL, 0);
        if (sampleRate > 0) {
            return (long long)((length * 1000) / sampleRate);
        }
    }
    return 0;
}

void player_cleanup() {
    if (sound_playing) {
        ma_sound_uninit(&current_sound);
        sound_playing = false;
    }
    if (is_initialized) {
        ma_engine_uninit(&engine);
        is_initialized = false;
    }
    if (context_initialized) {
        ma_context_uninit(&context);
        context_initialized = false;
    }
}

void player_set_volume(int percent) {
    if (percent <= 100) {
        current_volume = (float)percent / 100.0f;
    } else {
        // Overdrive: Scale aggressively up to 10.0x gain (20 dB) for maximum loudness
        float t = (percent - 100.0f) / 150.0f; // 0.0 to 1.0
        current_volume = 1.0f + (t * 9.0f);
    }
    
    if (sound_playing) {
        ma_sound_set_volume(&current_sound, current_volume);
    }
}

void player_set_spatializer(int enabled) {
    spatializer_enabled = (enabled != 0);
    if (sound_playing) {
        ma_sound_set_spatialization_enabled(&current_sound, spatializer_enabled ? MA_TRUE : MA_FALSE);
        if (spatializer_enabled) {
            ma_engine_listener_set_position(&engine, 0, 0.0f, 0.0f, 0.0f);
            ma_sound_set_position(&current_sound, 0.0f, 0.0f, 1.0f);
        }
    }
}
