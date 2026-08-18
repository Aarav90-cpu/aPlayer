#include <stdio.h>
#include <stdlib.h>
#include <vlc/vlc.h>
#include <stdbool.h>

libvlc_instance_t * inst = NULL;
libvlc_media_player_t *mp = NULL;

void player_init() {
    if (inst == NULL) {
        inst = libvlc_new(0, NULL);
    }
}

void player_play(const char *filepath) {
    if (inst == NULL) return;
    
    // If something is already playing, stop it and release
    if (mp != NULL) {
        libvlc_media_player_stop(mp);
        libvlc_media_player_release(mp);
    }

    libvlc_media_t *m;
    // We assume filepath is a local file path
    m = libvlc_media_new_path(inst, filepath);
    mp = libvlc_media_player_new_from_media(m);
    libvlc_media_release(m);

    libvlc_media_player_play(mp);
}

void player_pause() {
    if (mp != NULL) {
        libvlc_media_player_pause(mp);
    }
}

void player_stop() {
    if (mp != NULL) {
        libvlc_media_player_stop(mp);
    }
}

int player_is_playing() {
    if (mp != NULL) {
        return libvlc_media_player_is_playing(mp);
    }
    return 0;
}

float player_get_position() {
    if (mp != NULL) {
        return libvlc_media_player_get_position(mp);
    }
    return 0.0f;
}

void player_set_position(float pos) {
    if (mp != NULL) {
        libvlc_media_player_set_position(mp, pos);
    }
}

long long player_get_length() {
    if (mp != NULL) {
        return libvlc_media_player_get_length(mp); // in ms
    }
    return 0;
}

void player_cleanup() {
    if (mp != NULL) {
        libvlc_media_player_stop(mp);
        libvlc_media_player_release(mp);
        mp = NULL;
    }
    if (inst != NULL) {
        libvlc_release(inst);
        inst = NULL;
    }
}
