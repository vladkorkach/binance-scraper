from master import Master
import logging
import time
import logging.handlers

logger = logging.getLogger("scrapper")
logger.setLevel(logging.DEBUG)

fh = logging.handlers.RotatingFileHandler("logs/scrapper.log", maxBytes=100000, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
formatter.converter = time.gmtime
fh.setFormatter(formatter)
logger.addHandler(fh)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

manager = Master()

if __name__ == "__main__":
    manager.start()
