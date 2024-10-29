FROM python:3.10
WORKDIR /app

ENV TZ="Europe/Rome"

## Install Firefox and other dependencies
RUN apt-get update && \
apt-get install -y firefox-esr wget gnupg build-essential rustc cargo && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

# Download and install GeckoDriver for ARM64
RUN wget -q https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux-aarch64.tar.gz -O /tmp/geckodriver.tar.gz && \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin && \
    chmod +x /usr/local/bin/geckodriver && \
    rm /tmp/geckodriver.tar.gz

# Copy the requirements.txt and install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .

CMD [ "python3", "./bot.py"]