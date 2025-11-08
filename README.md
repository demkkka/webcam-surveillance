# Motion Detector with Telegram Notifications

A motion detection program using a webcam with automatic photo sending to Telegram.

## Features

- 🎥 **Real-time motion detection** - video stream analysis from webcam
- 📸 **Automatic photo sending** when motion is detected
- ⏰ **Daily scheduled photos** - sends a photo every day at exactly 2:00 PM

## Requirements

- Python 3.7+
- Webcam
- Telegram bot token
- Telegram chat ID

## Installation

1. Clone the repository:
```
git clone https://github.com/demkkka/webcam-surveillance.git
cd webcam-surveillance
```
2. Create a virtual environment:
```
# On Windows
python -m venv venv

# On macOS/Linux
python3 -m venv venv
```
3. Activate the virtual environment:
```
# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```
4. Install all the dependencies:
```
pip install -r requirements.txt
```
5. Create a `.env` file in the project root:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### How to Get Telegram Bot Token and Chat ID

1. **Bot Token:**
   - Find [@BotFather](https://t.me/botfather) on Telegram
   - Send the `/newbot` command
   - Follow the instructions to create a bot
   - Copy the received token

2. **Chat ID:**
   - Message [@userinfobot](https://t.me/userinfobot)
   - It will send you your Chat ID
   - Or use your username (starts with @)

## Usage

Run the program:
```
python main.py
```
The program will automatically:
- Start monitoring motion through the webcam
- Send photos to Telegram when motion is detected
- Send a photo every day at exactly **2:00 PM (14:00)**

To stop, press `Ctrl+C`

## Configuration

You can change settings in the `main.py` file:

### Motion Detection
```
MIN_CONTOUR_AREA = 5000  # Minimum contour area for motion detection
SEND_INTERVAL = 3        # Minimum interval (in seconds) between photo sends
```
### Daily Photo Time
```
DAILY_PHOTO_TIME = dt_time(14, 0)  # Format: (hours, minutes)
```
Examples:
- `dt_time(9, 30)` - 9:30 AM
- `dt_time(18, 0)` - 6:00 PM
- `dt_time(23, 45)` - 11:45 PM

```
## How It Works

1. **Motion Detection:**
   - Uses Background Subtraction algorithm (MOG2)
   - Applies morphological operations to reduce noise
   - Analyzes contours to determine significant motion

2. **Motion-Based Sending:**
   - Captures a frame when motion is detected
   - Sends photo to Telegram with timestamp
   - Respects minimum interval between sends

3. **Daily Scheduled Photo:**
   - Runs in parallel with motion detection
   - Automatically calculates time until next send
   - Sends photo at exactly the specified time
