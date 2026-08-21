#define MINIAUDIO_IMPLEMENTATION
#include "miniaudio.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <pthread.h>
#include <math.h>
#include <sys/time.h>

#define MAX_FADEOUT_SOUNDS 10
#define PI 3.14159265358979323846

typedef struct {
    ma_sound sound;
    bool active;
    long long start_time_ms;
    float start_volume;
} FadeoutSound;

FadeoutSound fadeout_sounds[MAX_FADEOUT_SOUNDS];

ma_engine engine;
ma_sound current_sound;
bool is_initialized = false;
bool sound_playing = false;
float current_volume = 1.0f; // 100%
bool spatializer_enabled = false;
// Removed context as we now use miniaudio's internal context management

// Crossfade settings
int max_overlap = 2; // Default
int crossfade_duration_ms = 0;
int crossfade_curve_type = 0; // 0=Linear, 1=EqualPower, 2=Exponential, 3=Logarithmic, 4=S-Curve
long long current_sound_start_time_ms = 0;

// Fader thread
pthread_t fader_thread;
bool fader_thread_running = false;
pthread_mutex_t fader_mutex = PTHREAD_MUTEX_INITIALIZER;

long long get_time_ms() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (long long)(tv.tv_sec) * 1000 + (tv.tv_usec) / 1000;
}

float calculate_fade_volume(float t, int type, bool is_fade_in) {
    if (t < 0.0f) t = 0.0f;
    if (t > 1.0f) t = 1.0f;
    
    float x = is_fade_in ? t : (1.0f - t);
    float vol = 0.0f;
    
    switch (type) {
        case 0: // Linear
            vol = x;
            break;
        case 1: // Equal Power
            vol = sinf(x * PI / 2.0f);
            break;
        case 2: // Exponential
            vol = x * x;
            break;
        case 3: // Logarithmic
            vol = log10f(1.0f + 9.0f * x);
            break;
        case 4: // S-Curve
            vol = x * x * (3.0f - 2.0f * x);
            break;
        default:
            vol = x;
            break;
    }
    return vol;
}

void* fader_thread_func(void* arg) {
    while (fader_thread_running) {
        pthread_mutex_lock(&fader_mutex);
        long long now = get_time_ms();
        
        // Handle fadeout sounds
        for (int i = 0; i < MAX_FADEOUT_SOUNDS; i++) {
            if (fadeout_sounds[i].active) {
                long long elapsed = now - fadeout_sounds[i].start_time_ms;
                if (elapsed >= crossfade_duration_ms || crossfade_duration_ms == 0) {
                    ma_sound_stop(&fadeout_sounds[i].sound);
                    ma_sound_uninit(&fadeout_sounds[i].sound);
                    fadeout_sounds[i].active = false;
                } else {
                    float t = (float)elapsed / (float)crossfade_duration_ms;
                    float fade_vol = calculate_fade_volume(t, crossfade_curve_type, false);
                    ma_sound_set_volume(&fadeout_sounds[i].sound, fadeout_sounds[i].start_volume * fade_vol);
                }
            }
        }
        
        // Handle current sound fade in
        if (sound_playing) {
            long long elapsed = now - current_sound_start_time_ms;
            if (elapsed < crossfade_duration_ms && crossfade_duration_ms > 0) {
                float t = (float)elapsed / (float)crossfade_duration_ms;
                float fade_vol = calculate_fade_volume(t, crossfade_curve_type, true);
                ma_sound_set_volume(&current_sound, current_volume * fade_vol);
            } else {
                ma_sound_set_volume(&current_sound, current_volume);
            }
        }
        
        pthread_mutex_unlock(&fader_mutex);
        usleep(10000); // 10ms
    }
    return NULL;
}

void player_init() {
    if (!is_initialized) {
        for (int i = 0; i < MAX_FADEOUT_SOUNDS; i++) {
            fadeout_sounds[i].active = false;
        }

        ma_engine_config engineConfig = ma_engine_config_init();

        if (ma_engine_init(&engineConfig, &engine) != MA_SUCCESS) {
            printf("Failed to initialize miniaudio engine.\n");
            return;
        }
        
        fader_thread_running = true;
        pthread_create(&fader_thread, NULL, fader_thread_func, NULL);
        
        is_initialized = true;
    }
}

void enforce_max_overlap() {
    int active_count = 0;
    for (int i = 0; i < MAX_FADEOUT_SOUNDS; i++) {
        if (fadeout_sounds[i].active) active_count++;
    }
    
    while (active_count >= max_overlap && active_count > 0) {
        // Find oldest
        long long oldest_time = -1;
        int oldest_idx = -1;
        for (int i = 0; i < MAX_FADEOUT_SOUNDS; i++) {
            if (fadeout_sounds[i].active) {
                if (oldest_time == -1 || fadeout_sounds[i].start_time_ms < oldest_time) {
                    oldest_time = fadeout_sounds[i].start_time_ms;
                    oldest_idx = i;
                }
            }
        }
        if (oldest_idx != -1) {
            ma_sound_stop(&fadeout_sounds[oldest_idx].sound);
            ma_sound_uninit(&fadeout_sounds[oldest_idx].sound);
            fadeout_sounds[oldest_idx].active = false;
            active_count--;
        } else {
            break;
        }
    }
}

void player_play(const char *filepath) {
    if (!is_initialized) return;

    pthread_mutex_lock(&fader_mutex);

    if (sound_playing) {
        if (crossfade_duration_ms > 0 && max_overlap > 0) {
            enforce_max_overlap();
            // Find empty slot
            int slot = -1;
            for (int i = 0; i < MAX_FADEOUT_SOUNDS; i++) {
                if (!fadeout_sounds[i].active) {
                    slot = i;
                    break;
                }
            }
            if (slot != -1) {
                fadeout_sounds[slot].sound = current_sound;
                fadeout_sounds[slot].active = true;
                fadeout_sounds[slot].start_time_ms = get_time_ms();
                // Get current fade volume
                long long elapsed = fadeout_sounds[slot].start_time_ms - current_sound_start_time_ms;
                float start_fade_vol = 1.0f;
                if (elapsed < crossfade_duration_ms) {
                    start_fade_vol = calculate_fade_volume((float)elapsed / crossfade_duration_ms, crossfade_curve_type, true);
                }
                fadeout_sounds[slot].start_volume = current_volume * start_fade_vol;
            } else {
                ma_sound_uninit(&current_sound);
            }
        } else {
            ma_sound_stop(&current_sound);
            ma_sound_uninit(&current_sound);
        }
        sound_playing = false;
    }

    if (ma_sound_init_from_file(&engine, filepath, MA_SOUND_FLAG_STREAM, NULL, NULL, &current_sound) != MA_SUCCESS) {
        printf("Failed to load sound file: %s\n", filepath);
        pthread_mutex_unlock(&fader_mutex);
        return;
    }
    
    // Spatializer removed as it causes vocal phase cancellation (karaoke effect) and overrides volume.
    // Dolby Spoof will remain in UI but will not downmix to mono.
    
    current_sound_start_time_ms = get_time_ms();
    
    if (crossfade_duration_ms > 0) {
        printf("aPlayer [DEBUG]: Setting volume to 0.0 for crossfade %d ms\n", crossfade_duration_ms);
        ma_sound_set_volume(&current_sound, 0.0f);
    } else {
        printf("aPlayer [DEBUG]: Setting volume to %f (no crossfade)\n", current_volume);
        ma_sound_set_volume(&current_sound, current_volume);
    }
    
    ma_sound_start(&current_sound);
    sound_playing = true;
    printf("aPlayer [DEBUG]: Sound started successfully. sound_playing = true\n");
    
    pthread_mutex_unlock(&fader_mutex);
}

void player_pause() {
    pthread_mutex_lock(&fader_mutex);
    if (sound_playing && ma_sound_is_playing(&current_sound)) {
        ma_sound_stop(&current_sound);
    } else if (sound_playing) {
        ma_sound_start(&current_sound);
    }
    pthread_mutex_unlock(&fader_mutex);
}

void player_stop() {
    pthread_mutex_lock(&fader_mutex);
    if (sound_playing) {
        ma_sound_stop(&current_sound);
        ma_sound_seek_to_pcm_frame(&current_sound, 0);
    }
    pthread_mutex_unlock(&fader_mutex);
}

int player_is_playing() {
    int playing = 0;
    pthread_mutex_lock(&fader_mutex);
    if (sound_playing && ma_sound_is_playing(&current_sound)) {
        playing = 1;
    }
    pthread_mutex_unlock(&fader_mutex);
    return playing;
}

float player_get_position() {
    float pos = 0.0f;
    pthread_mutex_lock(&fader_mutex);
    if (sound_playing) {
        ma_uint64 cursor;
        ma_uint64 length;
        ma_sound_get_cursor_in_pcm_frames(&current_sound, &cursor);
        ma_sound_get_length_in_pcm_frames(&current_sound, &length);
        if (length > 0) {
            pos = (float)cursor / (float)length;
        }
    }
    pthread_mutex_unlock(&fader_mutex);
    return pos;
}

void player_set_position(float pos) {
    pthread_mutex_lock(&fader_mutex);
    if (sound_playing) {
        ma_uint64 length;
        ma_sound_get_length_in_pcm_frames(&current_sound, &length);
        ma_sound_seek_to_pcm_frame(&current_sound, (ma_uint64)(pos * length));
    }
    pthread_mutex_unlock(&fader_mutex);
}

long long player_get_length() {
    long long len = 0;
    pthread_mutex_lock(&fader_mutex);
    if (sound_playing) {
        ma_uint64 length;
        ma_uint32 sampleRate;
        ma_sound_get_length_in_pcm_frames(&current_sound, &length);
        ma_sound_get_data_format(&current_sound, NULL, NULL, &sampleRate, NULL, 0);
        if (sampleRate > 0) {
            len = (long long)((length * 1000) / sampleRate);
        }
    }
    pthread_mutex_unlock(&fader_mutex);
    return len;
}

void player_cleanup() {
    fader_thread_running = false;
    if (is_initialized) {
        pthread_join(fader_thread, NULL);
    }
    
    pthread_mutex_lock(&fader_mutex);
    for (int i = 0; i < MAX_FADEOUT_SOUNDS; i++) {
        if (fadeout_sounds[i].active) {
            ma_sound_uninit(&fadeout_sounds[i].sound);
            fadeout_sounds[i].active = false;
        }
    }
    
    if (sound_playing) {
        ma_sound_uninit(&current_sound);
        sound_playing = false;
    }
    
    if (is_initialized) {
        ma_engine_uninit(&engine);
        is_initialized = false;
    }
    // Engine destroys its own context automatically if we didn't provide one.
    pthread_mutex_unlock(&fader_mutex);
}

void player_set_volume(int percent) {
    pthread_mutex_lock(&fader_mutex);
    if (percent <= 100) {
        current_volume = (float)percent / 100.0f;
    } else {
        float t = (percent - 100.0f) / 150.0f; // 0.0 to 1.0
        current_volume = 1.0f + (t * 9.0f);
    }
    
    if (sound_playing && crossfade_duration_ms == 0) {
        ma_sound_set_volume(&current_sound, current_volume);
    }
    pthread_mutex_unlock(&fader_mutex);
}

void player_set_spatializer(int enabled) {
    pthread_mutex_lock(&fader_mutex);
    spatializer_enabled = (enabled != 0);
    // Spatializer logic removed to preserve vocals and stereo field.
    pthread_mutex_unlock(&fader_mutex);
}

void player_set_crossfade(int duration_ms, int curve_type) {
    pthread_mutex_lock(&fader_mutex);
    crossfade_duration_ms = duration_ms;
    crossfade_curve_type = curve_type;
    pthread_mutex_unlock(&fader_mutex);
}

void player_set_max_overlap(int count) {
    pthread_mutex_lock(&fader_mutex);
    if (count < 1) count = 1;
    if (count > MAX_FADEOUT_SOUNDS) count = MAX_FADEOUT_SOUNDS;
    max_overlap = count;
    pthread_mutex_unlock(&fader_mutex);
}
