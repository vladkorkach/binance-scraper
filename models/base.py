# coding=utf-8

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

engine = create_engine('mysql://root:root@localhost/binance_scrapper_test')
Session = sessionmaker(bind=engine)

Base = declarative_base()
