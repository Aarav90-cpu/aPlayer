# aPlayer

A music player built for Linux.

## Build Instructions

### Dependencies

Ensure the following are installed on your system:
- `python3`
- `gcc`
- `make`
- `libtagc0-dev` (TagLib C bindings for metadata extraction)
- `pkg-config`
- Python dependencies (e.g., `pywebview`)

### Compiling the Core

1. Navigate to the core directory and compile the C backend:
   ```bash
   cd core
   make
   ```

### Running the Application

1. Run the Python bridge:
   ```bash
   python3 bridge/main.py
   ```
