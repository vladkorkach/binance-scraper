from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref
from . import Base


class Asset(Base):
    __tablename__="assets"
    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    free = Column(Float)
    fixed = Column(Float)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    account = relationship("Account", backref="my_assets")

    eth_value = Column(Float)
    quote_price = Column(Float)
    pair_name = Column(String(32))
    timestamp = Column(DateTime)  #the last time the asset eth value was updated

    def __repr__(self):
        return '<Asset {}>'.format(self.name)
