#!/usr/bin/env bash

# --- This script was designed for setting up a Selenium testing environment on a Linux system ---

RED='\033[0;31m'
NC='\033[0m'

echo "${RED}[!!!] Setup variables${NC}"
#https://developer.chrome.com/docs/chromedriver/downloads?hl=ru
# currect chrome version: 130.0.6723.58-1
CHROME_DRIVER=https://storage.googleapis.com/chrome-for-testing-public/130.0.6723.58/linux64/chromedriver-linux64.zip
DRIVER_ZIP_PATH="/tmp/chromedriver-linux64.zip"
DRIVER_EXTRACTION_PATH="/tmp/chromedriver-linux64"
SIGNING_KEY_PATH="/etc/apt/trusted.gpg.d/google-signing-key.pub"
CHROME_DEB_PATH="/tmp/google-chrome-amd64.deb"
DRIVER_BINARY_PATH="/usr/local/bin/chromedriver"

echo "${RED}[!!!] Install dependencies${NC}"
sudo apt-get install -y wget unzip openjdk-8-jre-headless

echo "${RED}[!!!] Remove existing downloads and binaries${NC}"
sudo apt remove -y google-chrome-stable
sudo rm $SIGNING_KEY_PATH
sudo rm $CHROME_DEB_PATH
sudo rm $DRIVER_BINARY_PATH
sudo rm -rf $DRIVER_EXTRACTION_PATH
sudo rm $DRIVER_ZIP_PATH

echo "${RED}[!!!] Install Chrome${NC}"
# Add Google signing key
curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub > /tmp/google-signing-key.pub
sudo mkdir /etc/apt/trusted.gpg.d
sudo mv /tmp/google-signing-key.pub $SIGNING_KEY_PATH
sudo apt-get -y update
sudo apt-get -y install google-chrome-stable

echo "${RED}[!!!] Install ChromeDriver${NC}"
wget -N $CHROME_DRIVER -P /tmp/
sudo unzip $DRIVER_ZIP_PATH -d /tmp/
sudo rm -rf $DRIVER_ZIP_PATH
sudo mv $DRIVER_EXTRACTION_PATH/chromedriver $DRIVER_BINARY_PATH
# sudo rm -rf $DRIVER_EXTRACTION_PATH
sudo chown root:root $DRIVER_BINARY_PATH
sudo chmod 0755 $DRIVER_BINARY_PATH
