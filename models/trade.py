from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from . import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    tradeId = Column(Integer)
    orderId = Column(Integer)
    symbol = Column(String(32))
    price = Column(Float)
    qty = Column(Float)
    commission = Column(Float)
    commissionAsset = Column(String(32))
    time = Column(DateTime)
    isBuyer = Column(Boolean)
    isMaker = Column(Boolean)
    isBestMatch = Column(Boolean)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    account = relationship("Account", backref="my_trades")
    raw_json = Column(Text)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'tradeId': self.tradeId,
            'orderId': self.orderId,
            'symbol': self.symbol,
            'price': self.price,
            'qty': self.qty,
            'commission': self.commission,
            'commissionAsset': self.commissionAsset,
            'time': self.time,
            'isBuyer': self.isBuyer,
            'isMaker': self.isMaker,
            'isBestMatch': self.isBestMatch
        }

    def __repr__(self):
        return '<Trade {}>'.format(self.tradeId)
