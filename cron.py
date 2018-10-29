'''
updates the portfolio every 5 minutes
'''
import time
import logging
from threading import Thread
from binance.exceptions import BinanceAPIException

logger = logging.getLogger("scrapper.cronjob")


class Cron(Thread):

    def __init__(self, accounts):
        Thread.__init__(self)
        self.accounts = accounts
        self.keep_running = True
        self.name = "Cron"

    def run(self):
        account_index = 0
        error_count = 0
        while self.keep_running:
            exception_occured = False
            try:
                account = self.accounts[account_index]
                logger.info(f"Updating the eth values for {account.api_key}")
                balances = account.get_asset_balances()
                account.post_assets(balances)
                account.update_account_portfolio()
                account_index += 1
            except BinanceAPIException as e:
                exception_occured = True
                account.post_error(e)
                if int(e.code) in [-2010, -1010, -2011]:
                    logger.info(f"{account.name}, {e.message}")
                elif int(e.code) == -1013:
                    #balance below minimum allowable, should get here if we checking balances, end trade
                    logger.info(f"{account.name} cannot , {e.message}")
                elif int(e.code) == -2015:
                    logger.error(f"{account.name} {e.message}, exiting")
                    continue
                elif int(e.code) == -2013:
                    logger.error(e)
                    print("check this for invalid timestamp")
                    time.sleep(60)
                elif int(e.status_code) == 429:
                    logger.warning(f"{account.name} hit a rate limit, backing dowm for 1 minute")
                    time.sleep(60)
                elif int(e.status_code) == 418:
                    logger.error(f"{account.name} Ooops, IP has been auto banned")
                    time.sleep(300)
                    continue
                else:
                    logger.error(f"{account.name} uncaught API exception, {e.message}, {e.code}, {e.status_code}")
            except IndexError as e:
                account_index = 0
                error_count = 0
                time.sleep(300)  # sleep for 5 minutes
            except Exception as e:
                exception_occured = True
                logger.error(e)
                #raise e
            finally:
                if error_count > 5:
                    print("raised 5 errors. incrementing counter")
                    account_index += 1
                    error_count = 0
                if exception_occured:
                    error_count += 1

    def __del__(self):
        logger.error("cron job is exiting!! please restart bot")
