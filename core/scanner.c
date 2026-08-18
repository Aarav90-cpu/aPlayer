#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>
#include <taglib/tag_c.h>
#include "scanner.h"
#include "json_builder.h"

static int is_audio_file(const char *filename) {
    const char *ext = strrchr(filename, '.');
    if (!ext) return 0;
    if (strcasecmp(ext, ".mp3") == 0 ||
        strcasecmp(ext, ".flac") == 0 ||
        strcasecmp(ext, ".ogg") == 0 ||
        strcasecmp(ext, ".wav") == 0 ||
        strcasecmp(ext, ".m4a") == 0) {
        return 1;
    }
    return 0;
}

static unsigned long hash_string(const char *str) {
    unsigned long hash = 5381;
    int c;
    while ((c = *str++)) {
        hash = ((hash << 5) + hash) + c;
    }
    return hash;
}

static void scan_directory_recursive(const char *path, JsonBuilder *jb, int *is_first) {
    DIR *dir = opendir(path);
    if (!dir) return;

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }

        char full_path[1024];
        snprintf(full_path, sizeof(full_path), "%s/%s", path, entry->d_name);

        struct stat st;
        if (stat(full_path, &st) == 0) {
            if (S_ISDIR(st.st_mode)) {
                scan_directory_recursive(full_path, jb, is_first);
            } else if (S_ISREG(st.st_mode) && is_audio_file(entry->d_name)) {
                TagLib_File *file = taglib_file_new(full_path);
                const char *title = entry->d_name;
                const char *artist = "Unknown Artist";
                const char *album = "Unknown Album";
                char cover_path[256] = "";
                
                if (file != NULL) {
                    if (taglib_file_is_valid(file)) {
                        TagLib_Tag *tag = taglib_file_tag(file);
                        if (tag != NULL) {
                            char *t = taglib_tag_title(tag);
                            char *a = taglib_tag_artist(tag);
                            char *al = taglib_tag_album(tag);
                            if (t && strlen(t) > 0) title = t;
                            if (a && strlen(a) > 0) artist = a;
                            if (al && strlen(al) > 0) album = al;
                        }
                    }
                    
                    TagLib_Complex_Property_Attribute*** props = taglib_complex_property_get(file, "PICTURE");
                    if (props != NULL) {
                        TagLib_Complex_Property_Picture_Data picture;
                        taglib_picture_from_complex_property(props, &picture);
                        if (picture.size > 0 && picture.data != NULL) {
                            unsigned long hash = hash_string(album);
                            char ext[8] = ".jpg";
                            if (picture.mimeType && strstr(picture.mimeType, "png")) strcpy(ext, ".png");
                            
                            snprintf(cover_path, sizeof(cover_path), ".cache/covers/%lu%s", hash, ext);
                            
                            struct stat st_cov;
                            if (stat(cover_path, &st_cov) != 0) {
                                FILE *fh = fopen(cover_path, "wb");
                                if (fh) {
                                    fwrite(picture.data, 1, picture.size, fh);
                                    fclose(fh);
                                }
                            }
                        }
                        taglib_complex_property_free(props);
                    }
                }

                if (!*is_first) {
                    jb_append(jb, ",");
                }
                *is_first = 0;

                jb_append(jb, "{\"path\":\"");
                jb_append_escaped(jb, full_path);
                jb_append(jb, "\",\"filename\":\"");
                jb_append_escaped(jb, entry->d_name);
                jb_append(jb, "\",\"title\":\"");
                jb_append_escaped(jb, title);
                jb_append(jb, "\",\"artist\":\"");
                jb_append_escaped(jb, artist);
                jb_append(jb, "\",\"album\":\"");
                jb_append_escaped(jb, album);
                jb_append(jb, "\",\"cover\":\"");
                jb_append_escaped(jb, cover_path);
                jb_append(jb, "\"}");

                if (file != NULL) {
                    taglib_tag_free_strings();
                    taglib_file_free(file);
                }
            }
        }
    }
    closedir(dir);
}

char* scanner_scan_folder(const char *folder_path) {
    JsonBuilder jb;
    jb_init(&jb);

    jb_append(&jb, "[");
    int is_first = 1;
    scan_directory_recursive(folder_path, &jb, &is_first);
    jb_append(&jb, "]");

    return jb.buffer;
}

void scanner_free_result(char* str) {
    free(str);
}
