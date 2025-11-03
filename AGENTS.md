# Coding Rules for kickstart

## Core Principles
- Maintainability > over-engineering
- Code clarity > documentation
- KISS (Keep It Simple, Stupid)

## Python Style
- Use functional patterns whenever possible through Python standard library
- Avoid introducing helpers just to force functional patterns
- Prefer built-in functions (map, filter, list comprehensions) over custom utilities
- Use type hints for function signatures
- Never use `Any` type - always provide proper type annotations
- Use `# fmt: off` and `# fmt: on` to preserve functional code style when Ruff's formatting breaks elegant patterns
  - Functional chains, pipelines, and compositional patterns should maintain their elegance
  - Don't let auto-formatting destroy intentional code structure

## Documentation
- No need for extensive documentation
- Code should be self-explanatory
- Prefer clear naming over comments
- Keep docstrings minimal - only generate them for util functions
  - Util functions are reusable helpers that may be used across multiple contexts
  - Main application logic, endpoints, and business logic should be self-explanatory without docstrings
- Never generate markdown files as documentation unless explicitly asked (no README.md, CONTRIBUTING.md, etc.)
  - Documentation should live in code comments when absolutely necessary
  - Project structure and usage should be self-evident

## General Guidelines
- Favor simplicity over cleverness
- Write code that is easy to read and modify
- Avoid premature optimization
- Don't abstract until there's a clear pattern that repeats
