#!/usr/bin/env bash

# --- This script was designed for setting up a Selenium testing environment on a Linux system ---

RED='\033[0;31m'
NC='\033[0m'

echo "${RED}[!!!] Setup variables${NC}"
#https://developer.chrome.com/docs/chromedriver/downloads?hl=ru
CHROME_DRIVER=https://storage.googleapis.com/chrome-for-testing-public/130.0.6723.58/linux64/chromedriver-linux64.zip
# currect chrome version: 130.0.6723.58-1

echo "${RED}[!!!] Install dependencies${NC}"
sudo apt-get install -y wget unzip openjdk-8-jre-headless

echo "${RED}[!!!] Remove existing downloads and binaries${NC}"
sudo apt remove -y google-chrome-stable
sudo rm /etc/apt/trusted.gpg.d/google-signing-key.pub
sudo rm /tmp/google-chrome-amd64.deb
sudo rm /usr/local/bin/chromedriver
sudo rm -rf /tmp/chromedriver-linux64
sudo rm /tmp/chromedriver-linux64.zip

echo "${RED}[!!!] Install Chrome${NC}"
# Add Google signing key
curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub > /tmp/google-signing-key.pub
sudo mkdir /etc/apt/trusted.gpg.d
sudo mv /tmp/google-signing-key.pub /etc/apt/trusted.gpg.d/
sudo apt-get -y update
sudo apt-get -y install google-chrome-stable

echo "${RED}[!!!] Install ChromeDriver${NC}"
wget -N $CHROME_DRIVER -P /tmp/
sudo unzip /tmp/chromedriver-linux64.zip -d /tmp/
rm /tmp/chromedriver-linux64.zip
sudo mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
sudo rm -rf /tmp/chromedriver-linux64
sudo chown root:root /usr/local/bin/chromedriver
sudo chmod 0755 /usr/local/bin/chromedriver