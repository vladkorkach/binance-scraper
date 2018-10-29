import threading
from twisted.internet import reactor
from threading import Thread
from account import Account
from scrapper import Scrapper
from cron import Cron
from models import Account as AccountModel, create_session
from sqlalchemy import exc
from twisted.internet import reactor
import logging, time
from var_dump import var_dump


logger = logging.getLogger("scrapper.master")


class Master(Thread):

    DEFAULT_QUOTES = ['ETHBTC', 'BNBETH', 'ETHUSDT']

    def __init__(self):
        Thread.__init__(self)

        self.cron = None
        self.accounts = []
        self.keep_running = True
        self.name = "Master"
        self.scrapper = None

    def run(self):
        with create_session() as session:
            #get api keys from server
            accounts_models = session.query(AccountModel).filter_by(active=True).all()
        print(f"we have {len(accounts_models)} accounts")
        for account_model in accounts_models:
            account = Account(account_model.api_key, account_model.api_secret, self)
            account.start()
            self.accounts.append(account)
        self.scrapper = Scrapper(self.accounts)
        self.scrapper.start()
        time.sleep(30)

        self.cron = Cron(self.accounts)
        self.cron.start()

        scrapped_accounts_keys = [account.api_key for account in self.accounts]
        while self.keep_running:
            time.sleep(10)   # last value 300
            logger.info("Checking the database for any new accounts")
            if reactor.running:
                print("the twisted reactor is running")
            else:
                print("the twisted reactor is not running")

            with create_session() as session:
                db_account_models = session.query(AccountModel).filter_by(active=True).all()
                unscrapped_accounts = []
                for account_model in db_account_models:
                    if account_model.api_key not in scrapped_accounts_keys:
                        logger.info(f"We have detected a new account, {account_model.api_key}")
                        account = Account(account_model.api_key, account_model.api_secret, self)
                        account.start()
                        self.accounts.append(account)
                        if account not in self.cron.accounts:
                            logger.info("adding the new account to the cron accounts")
                            self.cron.accounts.append(account)
                        unscrapped_accounts.append(account)
                        scrapped_accounts_keys.append(account.api_key)
                if unscrapped_accounts:
                    logger.info("scrapping new accounts")
                    scrapper = Scrapper(unscrapped_accounts)
                    scrapper.start()

                db_account_models_keys = [account.api_key for account in db_account_models]
                for account in self.accounts:
                    if account.api_key not in db_account_models_keys:
                        logger.info(f"account {account.api_key} has been deleted, stopping activities on it")
                        scrapped_accounts_keys.remove(account.api_key)
                        account.stop()
                        self.accounts.remove(account)

    def restart_scrapper(self):
        if not self.scrapper or not self.scrapper.is_alive():
            logger.info("restarting the scrapper")
            self.scrapper = Scrapper(self.accounts)
            self.scrapper.start()
