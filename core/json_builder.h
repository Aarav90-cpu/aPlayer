#ifndef JSON_BUILDER_H
#define JSON_BUILDER_H

#include <stddef.h>

typedef struct {
    char *buffer;
    size_t size;
    size_t capacity;
} JsonBuilder;

void jb_init(JsonBuilder *jb);
void jb_free(JsonBuilder *jb);
void jb_append(JsonBuilder *jb, const char *str);
void jb_append_escaped(JsonBuilder *jb, const char *str);

#endif
