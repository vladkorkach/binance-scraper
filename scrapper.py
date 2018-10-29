from threading import Thread
from exceptions import *
import logging
import time


logger = logging.getLogger("scrapper.scrapper")


class Scrapper(Thread):

    def __init__(self, accounts):
        Thread.__init__(self)
        self.accounts = accounts
        self.keep_running = True
        self.name = 'Scrapper'

    def old_run(self):
        loop_count = 0
        while self.keep_running:
            print(f"Loop no {loop_count}")
            for account in self.accounts:
                try:
                    account.update_account_trade_history()
                    if not self.keep_running:
                        break

                except BinanceAPIException as e:
                    account.post_error(e)
                    if int(e.code) in [-2010, -1010, -2011]:
                        logger.info(f"{account.name}, {e.message}")
                    elif int(e.code) == -1013:
                        #balance below minimum allowable, should get here if we checking balances, end trade
                        logger.info(f"{account.name} cannot , {e.message}")
                    elif int(e.code) == -2015:
                        logger.error(f"{account.name} {e.message}, exiting")
                        continue
                    elif int(e.status_code) == 429:
                        logger.warning(f"{account.name} hit a rate limit, backing dowm for 1 minute")
                        time.sleep(60)
                    elif int(e.status_code) == 418:
                        logger.error(f"{account.name} Ooops, IP has been auto banned")
                        time.sleep(300)
                        continue
                    else:
                        logger.error(f"{account.name} uncaught API exception, {e.message}, {e.code}, {e.status_code}")

                except KeyboardInterrupt:
                    logger.info("Received a keyboard interrupt")
                    self.keep_running = False
                    break
                except Exception as e: #default, for all uncaught exceptions.
                    account.post_error(e)
                    logger.error(f"{account.name} Exception, {e}")
            loop_count +=1
            self.keep_running = False
        logger.info("Scrapper is exiting, chill")

    def run(self):
        account_index = 0
        error_count = 0
        can_resume_update = False

        while self.keep_running:
            print(f"Account {account_index + 1}")
            exception_occured = False
            try:
                account = self.accounts[account_index]
                account.update_account_trade_history(resume_update=can_resume_update)
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
                elif int(e.status_code) == 429:
                    logger.warning(f"{account.name} hit a rate limit, backing dowm for 1 minute")
                    time.sleep(60)
                    can_resume_update = True
                elif int(e.status_code) == 418:
                    logger.error(f"{account.name} Ooops, IP has been auto banned")
                    time.sleep(300)
                    continue
                else:
                    logger.error(f"{account.name} uncaught API exception, {e.message}, {e.code}, {e.status_code}")

            except KeyboardInterrupt:
                exception_occured = True
                logger.info("Received a keyboard interrupt")
                self.keep_running = False
                break
            except IndexError:
                exception_occured = True
                logger.info(f"Finished scrapping, index at {account_index} for {len(self.accounts)} accounts")
                self.keep_running = False
            except Exception as e: #default, for all uncaught exceptions.
                exception_occured = True
                account.post_error(e)
                logger.error(f"{account.name} Exception, {e}")
            finally:
                if error_count > 5:
                    logger.error(f"Error scrapping account {account.api_key} !!")
                    account_index += 1
                    error_count = 0
                if exception_occured:
                    error_count += 1

        logger.info("Scrapper is exiting, chill")
