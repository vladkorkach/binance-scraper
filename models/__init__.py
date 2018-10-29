from .base import Base, engine, Session

#imports
from .account import Account
from .asset import Asset
from .trade import Trade
from .error_model import ErrorModel
from .portfolio import Portfolio
from sqlalchemy.exc import SQLAlchemyError
import logging, threading
from contextlib import contextmanager

logger = logging.getLogger('scrapper.model')

db_lock = threading.Lock()


@contextmanager
def create_session():
    session = None
    try:
        #generate database schema
        Base.metadata.create_all(engine)
        #create a new session
        session = Session()
        with db_lock:
            yield session
    except SQLAlchemyError as e:
        logger.error(e)
        raise e
    finally:
        if session:
            session.close()
