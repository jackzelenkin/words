from logging import StreamHandler
from logging import DEBUG
from logging import Formatter
from logging import Logger


def create_logger(name):
    logger = Logger(name)
    ch = StreamHandler()
    ch.setLevel(DEBUG)
    # create formatter and add it to the handlers
    formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)

    return logger