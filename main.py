import cv2
import numpy as np
import time
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, time as dt_time, timedelta

# Load environment variables
load_dotenv()

# Configuration from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Validate required environment variables
if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")

# Motion detection settings
MIN_CONTOUR_AREA = 5000
SEND_INTERVAL = 3

# Daily photo settings
DAILY_PHOTO_TIME = dt_time(14, 00)  # 14:00 (2 PM)

# Custom formatter to mask sensitive data
class SecureFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%', secrets=None):
        super().__init__(fmt, datefmt, style)
        self.secrets = secrets or []

    def format(self, record):
        # Format the message first
        formatted = super().format(record)

        # Mask all sensitive data
        for secret in self.secrets:
            if secret and len(secret) > 4:  # Only mask strings longer than 4 chars
                formatted = formatted.replace(secret, '***')
        return formatted

# Setup secure logging
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatter with secret masking
    formatter = SecureFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        secrets=[TELEGRAM_TOKEN, CHAT_ID]
    )

    # Console handler (stdout only)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handler to root logger
    logger.addHandler(console_handler)

    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

class MotionDetector:
    def __init__(self):
        # Validate token format (basic check)
        if not TELEGRAM_TOKEN or ':' not in TELEGRAM_TOKEN:
            raise ValueError("Invalid Telegram bot token format")

        self.bot = Bot(token=TELEGRAM_TOKEN)
        self.cap = cv2.VideoCapture(0)
        self.last_sent = 0
        self.frame_count = 0
        self.latest_frame = None  # Store latest frame for scheduled photo

        # Configure background subtractor
        self.back_sub = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=50,
            detectShadows=False
        )

        # Log safe information only
        logger.info("Motion detector initialized successfully")
        logger.info("Camera status: %s", self.cap.isOpened())
        logger.info("Min contour area: %s", MIN_CONTOUR_AREA)
        logger.info("Send interval: %s seconds", SEND_INTERVAL)
        logger.info("Daily photo time: %s", DAILY_PHOTO_TIME.strftime("%H:%M"))
        logger.info("Bot initialized: %s", bool(TELEGRAM_TOKEN and CHAT_ID))

    async def send_photo(self, frame, caption=None):
        """Asynchronously send photo to Telegram"""
        try:
            # Save frame to temporary file
            cv2.imwrite('motion.jpg', frame)
            with open('motion.jpg', 'rb') as photo:
                await self.bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=photo,
                    caption=caption or f'Motion detected! ({time.ctime()})'
                )
            logger.info("Photo sent successfully to Telegram")

            # Clean up temporary file
            try:
                os.remove('motion.jpg')
            except OSError:
                pass

        except TelegramError as e:
            # Log error without exposing sensitive data
            error_msg = str(e)
            # Basic sanitization of common sensitive patterns
            if TELEGRAM_TOKEN in error_msg:
                error_msg = error_msg.replace(TELEGRAM_TOKEN, '***')
            if CHAT_ID in error_msg:
                error_msg = error_msg.replace(CHAT_ID, '***')
            logger.error("Telegram send error: %s", error_msg)
        except Exception as e:
            logger.error("Unexpected error sending photo: %s", str(e))

    def process_frame(self, frame):
        """Process frame and detect motion"""
        try:
            # Reduce noise and convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # Apply background subtraction
            fg_mask = self.back_sub.apply(gray)

            # Morphological operations to reduce noise
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

            # Find contours
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Check if any contour is significant
            motion_detected = False
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > MIN_CONTOUR_AREA:
                    motion_detected = True
                    logger.debug("Significant motion detected - contour area: %s", area)
                    break

            return motion_detected

        except Exception as e:
            logger.error("Error processing frame: %s", str(e))
            return False

    async def daily_photo_scheduler(self):
        """Background task that sends photo at scheduled time"""
        logger.info("Daily photo scheduler started")

        while True:
            now = datetime.now()

            # Calculate next scheduled time
            scheduled_datetime = datetime.combine(now.date(), DAILY_PHOTO_TIME)

            # If scheduled time already passed today, schedule for tomorrow
            if now >= scheduled_datetime:
                scheduled_datetime += timedelta(days=1)

            # Calculate seconds until next scheduled time
            seconds_until_scheduled = (scheduled_datetime - now).total_seconds()

            logger.info("Next daily photo scheduled at: %s (in %.1f hours)",
                       scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                       seconds_until_scheduled / 3600)

            # Wait until scheduled time
            await asyncio.sleep(seconds_until_scheduled)

            # Send photo if we have a frame
            if self.latest_frame is not None:
                logger.info("Sending scheduled daily photo")
                await self.send_photo(
                    self.latest_frame,
                    f'Daily photo at {DAILY_PHOTO_TIME} ({datetime.now().strftime("%Y-%m-%d %H:%M")})'
                )
            else:
                logger.warning("No frame available for daily photo")

    async def run(self):
        """Main program loop"""
        logger.info("Starting motion detector...")

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    logger.error("Error reading frame from camera")
                    break

                # Store latest frame for scheduled photo
                self.latest_frame = frame.copy()

                motion = self.process_frame(frame)
                current_time = time.time()

                if motion and (current_time - self.last_sent) > SEND_INTERVAL:
                    logger.info("Motion detected - preparing to send photo")
                    await self.send_photo(frame)
                    self.last_sent = current_time

                # Limit frame processing rate
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal - shutting down")
        except Exception as e:
            logger.error("Unexpected error in main loop: %s", str(e))
        finally:
            self.cap.release()
            logger.info("Motion detector stopped")

async def main():
    try:
        detector = MotionDetector()

        # Run both motion detection and daily scheduler concurrently
        await asyncio.gather(
            detector.run(),
            detector.daily_photo_scheduler()
        )
    except ValueError as e:
        logger.error("Configuration error: %s", e)
    except Exception as e:
        logger.error("Failed to start motion detector: %s", e)

if __name__ == "__main__":
    asyncio.run(main())