from binance.client import Client
from custom_binance_websockets import BinanceSocketManager
from threading import Thread, Event
from binance.exceptions import BinanceAPIException
from datetime import datetime
from models import Trade, Asset, ErrorModel, create_session, Account as AccountModel, Portfolio
from helpers import get_portfolio_in_eth, StoppableThread
from requests.exceptions import ConnectionError
import logging
import time
import json


logger = logging.getLogger('scrapper.account')


class Account(StoppableThread):

    def __init__(self, api_key, api_secret, master):
        StoppableThread.__init__(self)
        self.symbol_counter = 0

        try:
            self.rest_client = Client(api_key, api_secret)
            self.ws_client = BinanceSocketManager(self.rest_client)
            self.keep_running = True
            self.api_key = api_key
            self.api_secret = api_secret
            self.name = f"Account {self.api_key}"

            self.master = master

        except ConnectionError as e:
            logger.error(e)

    def get_account_trade_history(self, symbol, start_time = None, from_id=None):
        try:
            if start_time:
                trades = self.rest_client.get_my_trades(symbol=symbol, startTime=start_time)
            elif from_id:
                trades = self.rest_client.get_my_trades(symbol=symbol, fromId=from_id)
            else:
                trades = self.rest_client.get_my_trades(symbol=symbol)
            return trades
        except Exception as e:
            raise e

    def get_asset_balances(self):
        try:
            account_info = self.rest_client.get_account()
            portfolio = account_info['balances']
            balances = [bal for bal in portfolio if float(bal['free']) or float(bal['locked'])]
            return balances
        except Exception as e:
            raise e

    def post_assets(self, balances):

        with create_session() as session:
            account = session.query(AccountModel).filter_by(api_key=self.api_key).first()
            account_assets = account.my_assets
            account_assets_names = [asset.name for asset in account_assets]
            for asset_params in balances:
                if not asset_params['asset'] in account_assets_names:  # asset is not yet created
                    asset = Asset(
                        name=asset_params['asset'],
                        free=asset_params['free'],
                        fixed=asset_params['locked'],
                        account=account
                    )
                    session.add(asset)
                    continue
                for account_asset in account_assets:
                    if asset_params['asset'] == account_asset.name:
                        account_asset.free = asset_params['free']
                        account_asset.fixed = asset_params['locked']
                        session.add(account_asset)
            #do the reverse, check if there is an asset whose balance is zero
            balances_assets_names = [asset['asset'] for asset in balances]
            for asset_name in account_assets_names:
                if asset_name not in balances_assets_names:
                    asset = [asset for asset in account_assets if asset.name == asset_name]
                    if asset:
                        asset = asset[0]
                        session.delete(asset)
                        logger.info(f"asset {asset_name} has been deleted")
            session.commit()

    def post_error(self, e):
        error_params = {'exception_name': e.__class__.__name__, 'message': e.message if hasattr(e, 'message') else f"{e}"}
        logger.error(f"{self.name} {e}")
        with create_session() as session:
            account = session.query(AccountModel).filter_by(api_key=self.api_key).first()
            error = ErrorModel(
                message=error_params['message'],
                exception_name=error_params['exception_name'],
                account=account
            )
            session.add(error)
            session.commit()

    def post_trades(self, trades, raw_json=None):

        with create_session() as session:
            account = session.query(AccountModel).filter_by(api_key=self.api_key).first()
            for trade_params in trades:
                trade_id = trade_params['id']
                trade_in_db = session.query(Trade).filter_by(tradeId=trade_id).first()
                if not trade_in_db:
                    trade = Trade(
                        tradeId=trade_params['id'],
                        orderId=trade_params['orderId'],
                        symbol=trade_params['symbol'],
                        price=trade_params['price'],
                        qty=trade_params['qty'],
                        commission=trade_params['commission'],
                        commissionAsset=trade_params['commissionAsset'],
                        time=datetime.fromtimestamp(float(trade_params['time']) / 1000),
                        isBuyer=trade_params['isBuyer'],
                        isMaker=trade_params['isMaker'],
                        isBestMatch=trade_params['isBestMatch'],
                        account=account,
                        raw_json=trade_params if not raw_json else raw_json
                    )
                    session.add(trade)
            session.commit()
        return True

    def process_user_socket_message(self, msg):
        # throw it in the database
        try:
            print(msg)
            payload = msg
            if payload['e'] == "outboundAccountInfo":
                balances_all = payload['B']
                balances = [{'asset': bal['a'], 'free': bal['f'], 'locked': bal['l']} for bal in balances_all if
                            float(bal['f']) or float(bal['l'])]

                self.post_assets(balances)

            elif payload['e'] == "executionReport":
                if payload['x'] == "TRADE":
                    logger.info(f"{self.name} received a trading event")
                    trade_params = {
                        'id': payload['t'],
                        'orderId': payload['i'],
                        'symbol': payload['s'],
                        'price': payload['L'],
                        'qty': payload['l'],
                        'commission': payload['n'],
                        'commissionAsset': payload['N'],
                        'time': payload['T'],
                        'isBuyer': not bool(payload['m']),
                        'isMaker': payload['m'],
                        'isBestMatch': None
                    }

                    self.post_trades([trade_params], raw_json=payload)
            elif payload['e'] == 'error':
                error = payload['m']
                logger.error(f"A network connection error occured, {error}")
                self.ws_client.stop_socket(self.user_socket_conn_key)
                #time.sleep(30)
                #self.start_account_socket()
            elif payload['e'] == 'connection_lost':
                #update last_update_time
                message = payload['m']
                logger.error(f"{message}")

            elif payload['e'] == 'connection_started':
                #update connection established
                message = payload['m']
                logger.info(f"{message}")
                self.master.restart_scrapper() #the only way to cover up for lost time
                self.ws_client._keepalive_user_socket()

            else:
                logger.error(f"unknown event, {msg}")
        except json.JSONDecodeError as e:
            logger.error(f"error occured, {e}")
            self.post_error(e)
        except Exception as e:
            logger.error(f"unknown error occurred, {e}")
            self.post_error(e)

    def start_account_socket(self):
        logger.info(f"{self.name} starting account socket")
        self.user_socket_conn_key = self.ws_client.start_user_socket(self.process_user_socket_message)
        self.ws_client.start()

    def update_account_portfolio(self):
        with create_session() as session:
            timestamp = datetime.utcnow()
            account = session.query(AccountModel).filter_by(api_key=self.api_key).first()
            if not account:
                raise ValueError("account not found")
            assets = account.my_assets
            portfolio_in_eth = get_portfolio_in_eth(assets)
            default_quotes = portfolio_in_eth['default_quotes']
            quote_dict = {}
            for default_quote in default_quotes:
                quote_dict[default_quote['symbol']] = default_quote['price']
            for asset_portfolio in portfolio_in_eth['portfolio']:
                asset = [asset for asset in assets if asset.name == asset_portfolio['symbol']]
                if asset:
                    asset = asset[0]
                    asset.eth_value = asset_portfolio['eth_cost']
                    asset.quote_price = asset_portfolio['price']
                    asset.pair_name = asset_portfolio['pair_name']
                    asset.timestamp = timestamp #last time the asset eth value was update
                    session.add(asset)

                    port = Portfolio(
                        account=account,
                        asset=asset,
                        asset_name=asset.name,
                        total_value=asset.free + asset.fixed,
                        eth_value=asset_portfolio['eth_cost'],
                        quote_price=asset_portfolio['price'],
                        pair_name=asset_portfolio['pair_name'],
                        timestamp=timestamp,
                        eth_btc_quote=quote_dict['ETHBTC'],
                        bnb_eth_quote=quote_dict['BNBETH'],
                        eth_usdt_quote=quote_dict['ETHUSDT']
                    )
                    session.add(port)
            session.commit()

    def update_account_trade_history(self, resume_update=False):
        '''
        brute force, there being no other way.
        :return:
        '''
        # 1. get all symbols.
        info = self.rest_client.get_exchange_info()
        symbols = [sym['symbol'] for sym in info['symbols']]

        if not resume_update: #a neat way to stop update from restart when it hits max requests per second
            self.symbol_counter = 0
            logger.info("updating all history")
        else:
            logger.info(f"starting the update at {self.symbol_counter}")
        while self.keep_running:
            try:
                symbol = symbols[self.symbol_counter]
                print(f"[+] Fetching the trades for {symbol}")
                start = time.time()
                trade_history = self.get_account_trade_history(symbol)
                if trade_history:
                    print(f"I got new trades, {trade_history}")
                    self.post_trades(trade_history)

                left = time.time() - start
                sleep_time = 0.2 - left
                if sleep_time > 0:
                    print(f"sleeping for {sleep_time}")
                    time.sleep(sleep_time)
                self.symbol_counter +=1
            except IndexError:
                self.symbol_counter = 0
                break
            except Exception as e:
                raise e


    def run(self):
        '''
        1.get account balances
            - check keys are okay and inform on bad keys
            - get balances
        2. start trade socket.

        :NOTE: updating history is done by scrapper class.
        :return:
        '''
        while self.keep_running:
            try:
                balances = self.get_asset_balances()
                self.post_assets(balances)

                self.start_account_socket()  #
                break

            except BinanceAPIException as e:
                self.post_error(e)
                if int(e.code) in [-2010, -1010, -2011]:
                    logger.info(f"{self.name}, {e.message}")
                elif int(e.code) == -1013:
                    # balance below minimum allowable, should get here if we checking balances, end trade
                    logger.info(f"{self.name} cannot , {e.message}")
                elif int(e.code) == -2015:  # api key error.
                    logger.error(f"{self.name} {e.message}, exiting")
                    break
                elif int(e.status_code) == 429:
                    logger.warning(f"{self.name} hit a rate limit, backing dowm for 1 minute")
                    time.sleep(60)
                elif int(e.status_code) == 418:
                    logger.error(f"{self.name} Ooops, IP has been auto banned")
                    time.sleep(300)
                else:
                    logger.error(f"{self.name} uncaught API exception, {e.message}, {e.code}, {e.status_code}")

            except Exception as e:  # default, for all uncaught exceptions.
                logger.error(f"{self.name} Exceptiion, {e}")
                self.post_error(e)
                raise e
