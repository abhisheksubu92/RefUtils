#! /usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author  : MG
@Time    : 2018/9/18 17:04
@File    : bitmex-ws_test.py
@contact : mmmaaaggg@163.com
@desc    : 
"""

# from bitmex_websocket import BitMEXWebsocket
# ws = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol="XBTUSD", api_key=None, api_secret=None)
from bitmex_websocket import BitMEXWebsocket
import logging
from logging.config import dictConfig
from time import sleep

# log settings
logging_config = dict(
    version=1,
    formatters={
        'simple': {
            'format': '%(asctime)s %(name)s|%(module)s.%(funcName)s:%(lineno)d %(levelname)s %(message)s'}
    },
    handlers={
        'file_handler':
            {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logger.log',
                'maxBytes': 1024 * 1024 * 10,
                'backupCount': 5,
                'level': 'DEBUG',
                'formatter': 'simple',
                'encoding': 'utf8'
            },
        'console_handler':
            {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'simple'
            }
    },

    root={
        'handlers': ['console_handler', 'file_handler'],  # , 'file_handler'
        'level': logging.DEBUG,
    }
)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)
logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)
dictConfig(logging_config)


# Basic use of websocket.
def run():
    logger = setup_logger()

    # Instantiating the WS will make it connect. Be sure to add your api_key/api_secret.
    ws = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol="XBTUSD", api_key=None, api_secret=None)
    # ws = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol="EOSUSD", api_key=None, api_secret=None)

    logger.info("Instrument data: %s" % ws.get_instrument())

    # Run forever
    while(ws.ws.sock.connected):
        logger.info("Ticker: %s" % ws.get_ticker())
        if ws.api_key:
            logger.info("Funds: %s" % ws.funds())
        logger.info("Market Depth: %s" % ws.market_depth())
        logger.info("Recent Trades: %s\n\n" % ws.recent_trades())
        sleep(10)
        break


def setup_logger():
    # Prints logger info to terminal
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Change this to DEBUG if you want a lot more info
    ch = logging.StreamHandler()
    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # add formatter to ch
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


if __name__ == "__main__":
    run()