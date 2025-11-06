ARG TARGETPLATFORM=linux/amd64

# -----------------------------------------------------------------------------
# Builder stage: compile the Python app into a single standalone binary
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    clang \
    ccache \
    patchelf \
    binutils \
    curl \
    file \
    && rm -rf /var/lib/apt/lists/*

# Install uv (astral) and move binaries into PATH
RUN curl -fsSL https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx

# Copy project sources required for the build
COPY pyproject.toml uv.lock ./
COPY kickstart.py ./
COPY src ./src
COPY config.json ./
COPY profiles ./profiles

# Create virtual environment and install build/runtime deps
RUN uv venv && \
    uv pip install nuitka ordered-set zstandard rich

# Run Nuitka to produce a single standalone binary.
RUN .venv/bin/python -m nuitka \
    --onefile \
    --standalone \
    --assume-yes-for-downloads \
    --include-data-dir=./profiles=profiles \
    --include-data-file=./config.json=config.json \
    --output-filename=kickstart \
    --output-dir=/app/dist \
    --include-package=src \
    --python-flag=-OO \
    --lto=yes \
    --jobs=4 \
    --clang \
    kickstart.py

# Prepare a tiny output directory that contains only the final binary.
RUN mkdir -p /out && \
    if [ -f /app/dist/kickstart ]; then \
    cp /app/dist/kickstart /out/kickstart && \
    chmod 0755 /out/kickstart ; \
    else \
    echo "Expected binary missing: /app/dist/kickstart" >&2 ; \
    ls -al /app/dist || true ; \
    false ; \
    fi

# -----------------------------------------------------------------------------
# Final stage: minimal image containing only the single binary
# -----------------------------------------------------------------------------
FROM scratch AS final
COPY --from=builder /out/kickstart /kickstart
