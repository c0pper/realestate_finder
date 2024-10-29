import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from scraping import scrape_listings, url, listings_dir
from dotenv import load_dotenv
import os
from llm import json_to_human

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

CHECK_INTERVAL = 3600*6

def check_job_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    if context.job_queue:
        current_jobs = context.job_queue.get_jobs_by_name(name)
        if not current_jobs:
            return False
        else:
            return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id
    logger.info(f"{update.message.from_user.name} started the task")

    if check_job_exists(f"{update.effective_chat.username} looking for real estate", context):
        await update.effective_message.reply_text("Bot già avviato")

    context.job_queue.run_repeating(
        launch_scraping, 
        interval=CHECK_INTERVAL, 
        first=3, 
        name=f"{update.effective_chat.username} looking for real estate", 
        chat_id=chat_id
    )
    
    text = (f"Bot avviato.")
    await update.effective_message.reply_text(text)


async def launch_scraping(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    job = context.job

    new_listings = scrape_listings(url=url, listings_dir=listings_dir)
    if new_listings:
        for l in new_listings:
            human_desc = json_to_human(l)
            listing_url = l["url"]
            await context.bot.send_message(job.chat_id, text=f'{human_desc}\n\nLink: {listing_url}')
    else:
        logger.info(f"No new listings")




async def delete_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_jobs = context.job_queue.jobs()
    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()
            logger.info(f"Deleted job: {job.name}")
            await context.bot.send_message(job.chat_id, text=f"Deleted job: {job.name}")
    else:
        await context.bot.send_message(update.effective_message.chat_id, text=f"No jobs active")
    current_jobs = context.job_queue.get_jobs_by_name(str(context._chat_id))
    logger.info(f"Current jobs: {current_jobs}")


async def show_current_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_jobs = context.job_queue.jobs()
    if current_jobs:
        for job in current_jobs:
            jobs_str = "\n\n".join([job.name for job in current_jobs])
            job.schedule_removal()
            logger.info(jobs_str)
            await context.bot.send_message(job.chat_id, text=jobs_str)
    else:
        await context.bot.send_message(update.effective_message.chat_id, text=f"No jobs active")
    logger.info(f"Current jobs: {current_jobs}")


def run_bot() -> None:
    """Run bot."""
    app = ApplicationBuilder().token(os.getenv("TELE_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("deletejobs", delete_jobs))
    app.add_handler(CommandHandler("showcurrentjobs", show_current_jobs))

    app.run_polling()



run_bot()