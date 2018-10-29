from sqlalchemy import Column, Integer, Text, ForeignKey, String
from sqlalchemy.orm import relationship
from . import Base


class ErrorModel(Base):

    __tablename__ = "errors"

    id = Column(Integer, primary_key=True)
    message = Column(Text())
    exception_name = Column(String(64))
    account_id = Column(Integer, ForeignKey('accounts.id'))
    account = relationship('Account', backref="my_errors")

    def __init__(self, message, exception_name, account):
        self.message = message
        self.exception_name = exception_name
        self.account = account
