# Contributing to aPlayer

First off, thank you for considering contributing to aPlayer! We welcome contributions from everyone. 

## How to Contribute

1. **Fork the Repository**: Start by forking the repository to your own GitHub account.
2. **Clone the Repository**: Clone your fork to your local machine.
3. **Create a Branch**: Create a new branch for your feature or bug fix (`git checkout -b feature/my-new-feature`).
4. **Make Changes**: Make your changes in the codebase.
5. **Test Your Changes**: Ensure your changes do not break existing functionality. You can compile the C core by running `make` in the `core` directory.
6. **Commit Your Changes**: Commit your changes with a descriptive commit message (`git commit -am 'Add some feature'`).
7. **Push to the Branch**: Push your changes to your branch (`git push origin feature/my-new-feature`).
8. **Create a Pull Request**: Open a pull request against the `main` branch of the original repository.

## Coding Standards

- **C Code**: Ensure any changes to the C core are robust and do not introduce memory leaks.
- **Python Code**: Follow PEP 8 guidelines for Python code in the bridge.
- **UI Code**: Use Material 3 guidelines for UI additions. Avoid adding heavy frontend frameworks or bundlers (Vite is strictly prohibited).

## Reporting Bugs

If you find a bug, please create an issue on GitHub with a detailed description of the problem, including steps to reproduce it and your environment details.
