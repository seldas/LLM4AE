FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Match server/Dockerfile runtime
RUN apt-get update && apt-get install -y python3.11 python3.11-venv python3-pip

# Match client/Dockerfile runtime
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs
