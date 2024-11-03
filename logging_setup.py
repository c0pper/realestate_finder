import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Create logs directory if it doesn't exist

    try:
        with open('/proc/cpuinfo', 'r') as cpuinfo:
            if 'Raspberry Pi' in cpuinfo.read():
                log_dir = '/app/logs'
            else:
                log_dir = '/home/simo/code/realestate_finder/logs'
    except FileNotFoundError:
        log_dir = '/home/simo/code/realestate_finder/logs'

    os.makedirs(log_dir, exist_ok=True)
    
    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create and configure file handler
    file_handler = RotatingFileHandler(
        f'{log_dir}/mail_sender.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Get the logger for this module
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Add the handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Configure httpx logger
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)
    
    return logger