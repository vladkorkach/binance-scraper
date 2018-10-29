from threading import Thread, Event
import requests
import logging

logger = logging.getLogger('scrapper.helper')
DEFAULT_QUOTES = ['ETHBTC', 'BNBETH', 'ETHUSDT']
base_assets = ['ETH', 'BTC', 'BNB', 'USDT']


class StoppableThread(Thread):

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop_event = Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


def get_quotes():

    resp = requests.get("https://api.binance.com/api/v3/ticker/price")
    pairs = resp.json()
    return pairs


def get_default_quotes(quotes = None):
    pairs = get_quotes() if not quotes else quotes
    market_quotes = []
    for quote_name in DEFAULT_QUOTES:
        market_quote = [quote for quote in pairs if quote['symbol'] == quote_name]
        if market_quote:
            market_quote = market_quote[0]
            market_quotes.append(market_quote)
    return market_quotes


def get_portfolio_in_eth(assets):
    quotes = get_quotes()
    portfolio = []
    for asset in assets:
        asset_portfolio = portfolio_in_eth(asset, quotes=quotes)
        portfolio.append(asset_portfolio)
    total = 0
    for asset in portfolio:
        total += asset['eth_cost']
    default_quotes = get_default_quotes(quotes)
    return {'total': total, 'portfolio': portfolio, 'default_quotes' : default_quotes}


def portfolio_in_eth(asset, quotes = None):
    pairs = get_quotes() if not quotes else quotes
    total_asset = float(asset.free) + float(asset.fixed) #sum up free and fixed assets in the account
    if asset.name == "ETH":
        return {'symbol': asset.name, 'qty': total_asset, 'eth_cost': total_asset, 'price' : 1, 'pair_name' : 'ETH'}
    for base_asset in base_assets:
        logger.debug(f"checking {base_asset} for {asset}")
        base_pairs = [pair for pair in pairs if base_asset in pair['symbol']] #get all quotes with only base
        asset_pair = [pair for pair in base_pairs if asset.name in pair['symbol']] #get the quote with asset from quotes with base
        if asset_pair:
            asset_pair = asset_pair[0] #unpack the asset if present
            #print(f"we are comparing against {asset_pair}")
            pair_name = asset_pair['symbol'] #for recording purposes, get the name of pair being compared
            pair_price = float(asset_pair['price']) #for recording purposes

            if asset_pair['symbol'].endswith(base_asset):  # eth is the base asset
                total_asset_cost = total_asset * float(asset_pair['price'])
            elif asset_pair['symbol'].startswith(base_asset):  # eth is the quote asset
                total_asset_cost = total_asset / float(asset_pair['price'])
            else:
                continue
            #print(f"first total asset cost is {total_asset_cost}")
            if not 'ETH' in asset_pair['symbol']:
                eth_pair = [pair for pair in base_pairs if 'ETH' in pair['symbol']] #our base asset changed because we did not find ETH pair
                #print(f"recomparing against {eth_pair}")
                if eth_pair:
                    asset_pair = eth_pair[0]
                    if asset_pair['symbol'].endswith(base_asset):  #the base asset has changed
                        total_asset_cost = total_asset_cost / float(asset_pair['price'])
                        #pair_price = pair_price / float(asset_pair['price'])

                    elif asset_pair['symbol'].startswith(base_asset):  # our base asset is the quote asset
                        total_asset_cost = total_asset_cost * float(asset_pair['price'])
                        #pair_price = pair_price * float(asset_pair['price'])

                    pair_name = f"{pair_name}"
            return {'symbol': asset.name,
                    'qty': total_asset,
                    'eth_cost': total_asset_cost,
                    'price': pair_price,
                    'pair_name' : pair_name}

