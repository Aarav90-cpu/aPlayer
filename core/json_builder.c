#include <stdlib.h>
#include <string.h>
#include "json_builder.h"

void jb_init(JsonBuilder *jb) {
    jb->capacity = 4096;
    jb->size = 0;
    jb->buffer = malloc(jb->capacity);
    jb->buffer[0] = '\0';
}

void jb_free(JsonBuilder *jb) {
    if (jb->buffer) {
        free(jb->buffer);
        jb->buffer = NULL;
    }
}

void jb_append(JsonBuilder *jb, const char *str) {
    if (!str) return;
    size_t len = strlen(str);
    while (jb->size + len + 1 > jb->capacity) {
        jb->capacity *= 2;
        jb->buffer = realloc(jb->buffer, jb->capacity);
    }
    strcpy(jb->buffer + jb->size, str);
    jb->size += len;
}

void jb_append_escaped(JsonBuilder *jb, const char *str) {
    if (!str) return;
    while (*str) {
        if (*str == '"') jb_append(jb, "\\\"");
        else if (*str == '\\') jb_append(jb, "\\\\");
        else if (*str == '\n') jb_append(jb, "\\n");
        else if (*str == '\r') jb_append(jb, "\\r");
        else if (*str == '\t') jb_append(jb, "\\t");
        else {
            char c[2] = {*str, '\0'};
            jb_append(jb, c);
        }
        str++;
    }
}
