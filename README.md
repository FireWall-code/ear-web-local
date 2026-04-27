# ear-web-local

This project is a Python-based bridge designed to resolve connection issues found in the original "ear-web" project. It enables stable Bluetooth communication between the web interface and your Nothing or CMF audio devices on Windows.

## Overview

The bridge acts as a local server that handles the low-level Bluetooth RFCOMM communication, which can sometimes be problematic when handled directly by the browser. By running this bridge, you ensure a more reliable experience when managing your earbuds' settings.

## Prerequisites

- **Python 3.10+**: Ensure Python is installed and added to your system's PATH.
- **Windows**: This bridge is currently optimized for Windows systems using PowerShell for device discovery.

## Getting Started

1. Clone or download this repository.
2. Run the `start.bat` file.
3. The script will check for Python, start the bridge, and automatically open the web interface at `http://localhost:3000`.
4. Click "Connect" in the web interface to link your device.

## LEGAL
This application and code is published under the GNU General Public License v3.0.
Nothing Technology Limited or any of its affiliates, subsidiaries, or related entities (collectively, “Nothing Technology”) is a valid licensee and can use this app for any purpose, including commercial purposes, without compensation to the developers of this app. Nothing Technology is not required to comply with the terms of the GNU General Public License v3.0.
This app is modified by the open-source community and is not affiliated with, sponsored by, or endorsed by Nothing Technology. The developers of this app take no responsibility for the accuracy or completeness of the content and materials provided in this app. The content and materials contained in this app, including but not limited to text, graphics, logos, images, and audio/visual materials, are proprietary to Nothing Technology Limited, 80 Cheapside, London EC2V 6EE and are protected by copyright, trademark, and other intellectual property laws. These materials may not be used without the express written permission of Nothing Technology. Nothing Technology reserves all rights.
