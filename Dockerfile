# Start with Ubuntu 22.04
FROM ubuntu:22.04

# Avoid prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    python3 \
    python3-pip \
    libopenmpi-dev \
    openmpi-bin \
    libfftw3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install LAMMPS 29Aug2024 (same version as your Windows installation)
WORKDIR /opt
RUN git clone -b stable_29Aug2024 https://github.com/lammps/lammps.git && \
    cd lammps && \
    mkdir build && \
    cd build && \
    cmake ../cmake \
        -D BUILD_SHARED_LIBS=ON \
        -D PKG_MOLECULE=ON \
        -D PKG_MANYBODY=ON \
        -D PKG_KSPACE=ON \
        -D PKG_RIGID=ON && \
    make -j4 && \
    make install && \
    cp lmp /usr/local/bin/lmp && \
    chmod +x /usr/local/bin/lmp

# Set up Python environment
RUN pip3 install --upgrade pip

# Copy your LAMMPS-Agents code
WORKDIR /app
COPY . /app/

# Install Python requirements
RUN pip3 install -r requirements.txt

# Install Playwright and its browser dependencies
RUN pip3 install playwright && \
    playwright install-deps && \
    playwright install chromium

# Set environment variables
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONPATH=/app

# Default command
CMD ["/bin/bash"]

