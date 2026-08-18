# aPlayer

A beautiful Music Player built explicitly for Linux.

- **Core**: Written in C (powered by `libvlc`)
- **Bridge**: Python (using `pywebview`)
- **UI**: HTML, CSS, and Material 3 Web Components (No Bundlers)

## Running the Player

1. Make sure `libvlc-dev` and `python3` are installed on your Linux system.
2. Compile the C core:
   ```bash
   cd core
   make
   ```
3. Install Python dependencies (ensure you have `pywebview` installed globally or in a virtual environment).
4. Run the player:
   ```bash
   python3 bridge/main.py
   ```

## Documentation
- See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute.
- See [CREDITS.md](CREDITS.md) for open-source library attributions.
- See [LICENSE](LICENSE) for licensing details.