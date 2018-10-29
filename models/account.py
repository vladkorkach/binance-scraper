from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship, backref
from helpers import get_portfolio_in_eth
from . import Base


class Account(Base):

    __tablename__="accounts"

    id = Column(Integer, primary_key=True)
    api_key = Column(String(128), index=True, unique=True)
    api_secret = Column(String(128), index=True, unique=True)
    assets = relationship('Asset', backref='owner', lazy='dynamic')
    trades = relationship('Trade', backref='owner', lazy='dynamic')
    errors = relationship('ErrorModel', backref='owner', lazy='dynamic')
    active = Column(Boolean, default=True)

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def get_portfolio(self):
        # use backref relationship to get each asset. get the value of each asset for tradepair against etherium.
        if self.assets:
            return get_portfolio_in_eth(self.assets)

    def __repr__(self):
        return '<Account {}>'.format(self.id)
