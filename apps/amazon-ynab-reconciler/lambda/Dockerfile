# Dockerfile for Amazon-YNAB Reconciler Lambda
# Uses container image for Playwright support

FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies for Playwright
RUN yum install -y \
    wget \
    unzip \
    libX11 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXtst \
    libXrandr \
    libXScrnSaver \
    alsa-lib \
    pango \
    atk \
    at-spi2-atk \
    gtk3 \
    && yum clean all

# Install Chromium dependencies
RUN yum install -y \
    nss \
    nspr \
    cups-libs \
    dbus-libs \
    libxkbcommon \
    libdrm \
    mesa-libgbm \
    && yum clean all

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN pip install playwright==1.40.0
RUN playwright install chromium

# Copy application code
COPY ../src/ ./src/
COPY ../config.yaml .
COPY lambda_handler.py .

# Set environment variables
ENV PYTHONPATH=/var/task/src
ENV PLAYWRIGHT_BROWSERS_PATH=/var/task/browsers
ENV HEADLESS_BROWSER=true

# Lambda handler
CMD ["lambda_handler.lambda_handler"]