from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref
from datetime import datetime
from . import Base


class Portfolio(Base):
    __tablename__ = "portfolio"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    account = relationship("Account", backref="my_assets_portfolio_history")
    asset_id = Column(Integer, ForeignKey('assets.id'))
    asset = relationship("Asset", backref="portfolio_history")
    asset_name=Column(String(32))
    total_value = Column(Float)
    eth_value = Column(Float)
    quote_price = Column(Float)
    pair_name = Column(String(32))
    timestamp = Column(DateTime)
    eth_btc_quote = Column(Float)
    bnb_eth_quote = Column(Float)
    eth_usdt_quote = Column(Float)

    def __repr__(self):
        return '<Portfolio {}>'.format(self.asset_name)
