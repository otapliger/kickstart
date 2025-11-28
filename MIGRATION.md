# Migration from Python to Go

Rewriting kickstart in Go for better build times and TUI capabilities.

## Status

- [x] Python code → `legacy/`
- [x] Root prepared for Go
- [ ] Go implementation

## Why Go

| Metric | Python/Nuitka | Go |
|--------|---------------|-----|
| Size | 8MB | 5-6MB |
| Build | 5-10min | 30sec |
| TUI | Rich | Bubble Tea |
| Cross-compile | Complex | `GOOS=linux go build` |

## Plan

### 1. Setup
- `go mod init`
- Dependencies: bubbletea, cobra, huh
- Basic CLI

### 2. Core
- Port context, validation, profiles
- JSON config loading

### 3. System
- Command execution
- GPU detection
- Input prompts
- Installation steps

### 4. TUI
- Bubble Tea model-update-view
- Status panel + progress
- Live output scrolling

### 5. Distros
- Arch/Void implementations
- Registry system

### 6. Polish
- Integration testing
- Build optimization
- Cross-compilation



## Key Differences

**Error handling**: Exceptions → explicit returns  
**TUI**: Imperative → functional (model-update-view)  
**Dependencies**: Rich → Bubble Tea ecosystem  

## File Mapping

```
legacy/kickstart.py    →  cmd/kickstart/main.go
legacy/src/context.py  →  pkg/context/
legacy/src/steps.py    →  pkg/steps/
legacy/src/tui.py      →  pkg/tui/
legacy/src/utils.py    →  pkg/utils/
legacy/src/distros/    →  pkg/distros/
```
