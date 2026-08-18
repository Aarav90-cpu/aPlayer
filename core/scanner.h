#ifndef SCANNER_H
#define SCANNER_H

// Scans a folder recursively, reads tags, and returns a JSON string.
// Caller is responsible for freeing the returned string using scanner_free_result.
char* scanner_scan_folder(const char *folder_path);

void scanner_free_result(char* str);

#endif
