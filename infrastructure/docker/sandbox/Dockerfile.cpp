# Hardened C++ execution sandbox
FROM gcc:12-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends bash \
    && apt-get remove -y wget curl git ssh \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Verify compiler available
RUN g++ --version

# No CMD — command supplied at runtime: g++ -O2 -o /tmp/prog /code/main.cpp && /tmp/prog