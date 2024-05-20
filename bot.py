import cv2
import numpy as np
from moviepy.editor import VideoFileClip
import os
import time
import shutil
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

## Admin ID (mine)
TRUSTED_USER_ID = 203151105

PHOTO = range(1)

## Function to replace green screen
def replace_green_screen(foreground, background):
    ## Convert the foreground to HSV
    hsv = cv2.cvtColor(foreground, cv2.COLOR_BGR2HSV)

    ## Define the green screen color range in HSV
    lower_green = np.array([35, 100, 100])
    upper_green = np.array([85, 255, 255])

    # Create a mask to detect green screen
    mask = cv2.inRange(hsv, lower_green, upper_green)

    ## Invert the mask to get the non-green parts
    mask_inv = cv2.bitwise_not(mask)

    ## Extract the non-green parts of the foreground
    fg_non_green = cv2.bitwise_and(foreground, foreground, mask=mask_inv)

    ## Extract the green screen parts of the background
    bg_green_part = cv2.bitwise_and(background, background, mask=mask)

    ## Combine the two parts
    combined = cv2.add(fg_non_green, bg_green_part)

    return combined


def igomeow(update: Update, context: CallbackContext) -> None:
    ## Prompt the user to send a photo for the igomeow effect.
    user_id = update.message.from_user.id
    ## Set user data
    context.user_data["user_id"] = user_id
    update.message.reply_text("Please send a photo for the igomeow effect.")
    return PHOTO


def cancel(update: Update, context: CallbackContext) -> None:
    ## Cancel the current operation.
    update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


def handle_photo(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    ## If user did not send igomeow comman, user_data[user_id] will be 0, therefore nothing will happen
    if user_id != context.user_data.get("user_id"):
        return ConversationHandler.END

    ## Handle photo messages.
    photo_file_id = update.message.photo[-1].file_id

    video_file_id = (
        "BAACAgIAAxkBAAMfZkpsSZH2-Uw1nSyLumFkvoFbOAwAAoBSAAIqL1BKQ7suxwONSDI1BA"
    )

    user_dir = f"user_data/{user_id}"
    os.makedirs(user_dir, exist_ok=True)

    video_file_path = os.path.join(user_dir, "video.mp4")
    photo_file_path = os.path.join(user_dir, "user_photo.jpg")
    output_path = os.path.join(user_dir, "output_video_with_audio.mp4")

    ## Get the video file
    video_file = context.bot.get_file(video_file_id)
    video_file.download(video_file_path)

    ## Get the photo file
    photo_file = context.bot.get_file(photo_file_id)
    photo_file.download(photo_file_path)

    ## Load green screen video
    video_clip = VideoFileClip(video_file_path)
    ## Load the background
    background = cv2.imread(photo_file_path)

    ## Get video properties
    frame_width = int(video_clip.w)
    frame_height = int(video_clip.h)
    fps = int(video_clip.fps)

    ## Resize background to the shape of the video
    background = cv2.resize(background, (frame_width, frame_height))

    def process_frame(frame):
        ## OpenCV works with BGR images by default
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        result_frame = replace_green_screen(frame, background)
        return cv2.cvtColor(result_frame, cv2.COLOR_BGR2RGB)

    processed_video_clip = video_clip.fl_image(process_frame)

    processed_video_clip.write_videofile(
        output_path, codec="libx264", audio_codec="aac"
    )

    ## Reply to the user with the igomeow video
    update.message.reply_video(open(output_path, "rb"))

    ## Clean user directory after video is sent back
    shutil.rmtree(user_dir)

    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    ## Replace 'YOUR TOKEN HERE' with your bot's token
    updater = Updater(TOKEN)

    ## Get the dispatcher to register handlers
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("igomeow", igomeow)],
        states={PHOTO: [MessageHandler(Filters.photo, handle_photo)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dp.add_handler(conv_handler)

    ## Start the Bot
    updater.start_polling()

    ## Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()


if __name__ == "__main__":
    main()
