from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Interval, create_engine
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
from hashlib import sha256
from sqlalchemy import func
from threading import Thread
from time import sleep

Base = declarative_base()

engine = create_engine('sqlite:///auction.db')

Session = sessionmaker(bind=engine)
session = Session()

def timedelta_to_hours( delta: timedelta ):
    return delta.total_seconds()/3600

def get_items() -> list:
    return session.query(Item).all()

def get_item_by_id(id: int):
    return session.query(Item).filter_by(id = id).first()

def get_user_by_name(username):
    return session.query(User).filter_by(username = username).first()

def get_user_by_id( id: int ):
    return session.query(User).filter_by(id = id).first()

def items_to_dict( items: list ) -> dict:
    return {"items": 
            list(
                map( 
                    lambda item: item.to_dict(), 
                    items
                )
            )
        }

def sha256_hash(text: str) -> str:
    return sha256( text.encode('utf-8') ).hexdigest()

def check_password( username, password ):
    user = get_user_by_name(username)
    return user and user.password == sha256_hash(password)

def create_user( username: str, email: str, password: str ) -> None:
    try:
        c_user = User( username = username, email = email, password = sha256_hash(password) )
        session.add( c_user )
        session.commit()
        return True
    except Exception as exp:
        print( f"Error: {exp}" )
        return False

def create_bid(username, among, item_id):
    try:
        user = get_user_by_name( username )
        item = get_item_by_id( item_id )
        bid = Bid( amount = among, bidder_id = user.id, item_id = item_id )
        item.current_price = among
        session.add(bid)
        session.commit()
        return True
    except Exception as exp:
        print( f"Error: {exp}" )
        return False

def create_item( username, title, description, starting_price, bid_increment, end_time, covers_files ):
    try:
        user = get_user_by_name( username )

        item = Item( 
            title = title,
            description = description,
            starting_price = starting_price,
            current_price = starting_price,
            end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M"),
            owner_id = user.id,
            covers_path = " ".join(covers_files),
            bid_increment = bid_increment,
        )
        session.add( item )
        session.commit()
        return True
    except Exception as error:
        print( error )
        return False

def create_coment_db( text, rating, author_id, seller_id ):
    if author_id == seller_id or rating < 0 or rating > 5 or len(text) == 0:
        print( "tyt" )
        return False

    dublicates = list(filter(lambda comment: comment.target_user_id == seller_id , get_user_by_id( author_id ).comments))
    
    print( dublicates )
    if len(dublicates) != 0:
        return False
    
    try:
        comment = Comment( 
            text =  text,
            rating = rating,
            author_id = author_id,
            target_user_id = seller_id
        )

        session.add( comment )
        session.commit()
        return True
    except Exception as error:
        print( error )
        return False

def get_comments_about_user( user_id ):
    return session.query( Comment ).filter_by( target_user_id = user_id ).all()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)

    items = relationship('Item', back_populates='owner')
    bids = relationship('Bid', back_populates='bidder')

    comments = relationship('Comment', back_populates='author')

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "items": [ item.to_dict() for item in self.items],
        }

class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    starting_price = Column(Float)
    bid_increment = Column(Float)       
    current_price = Column(Float)
    time_of_create = Column(DateTime, server_default=func.now())
    end_time = Column(DateTime)         
    covers_path = Column(String)
    closed = Column(Boolean, default = False)

    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship('User', back_populates='items')
    bids = relationship('Bid', back_populates='item')

    @property
    def buyer(self):
        if not self.closed:
            return None
        filtered_bids = list(filter( lambda bid: bid.time <= self.end_time , self.bids))
        if len(filtered_bids) != 0:
            return filtered_bids[-1].bidder

    @property
    def rating( self ):
        comments = get_comments_about_user( self.owner_id )
        if comments:
            filtered_comments = list(map(lambda comment: comment.rating, comments))
            if filtered_comments:
                return sum( filtered_comments ) / len( filtered_comments )

    def close(self):
        self.closed = True
        return self.buyer

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "title":        self.title,
            "description":  self.description,
            "starting_price":self.starting_price,
            "current_price":self.current_price,
            "covers_path":  self.covers_path,
            "main_cover_path":   self.covers_path.split()[0],
            "time_of_create": str(self.time_of_create.isoformat()),
            "end_time":     str(self.end_time.isoformat()),
            "owner_id":     self.owner_id,
            "owner_name":   self.owner.username,
            "bid_increment":self.bid_increment,
            "bid_history":  [ bid.to_dict() for bid in self.bids ],
            "closed":       self.closed,
            "buyer_name":   self.buyer.username if self.buyer else None,
            "rating":       self.rating,
        }

class Bid(Base):
    __tablename__ = 'bids'

    id = Column(Integer, primary_key=True)
    time = Column(DateTime, server_default=func.now())
    amount = Column(Float)

    bidder_id = Column(Integer, ForeignKey('users.id'))
    bidder = relationship('User', back_populates='bids')

    item_id = Column(Integer, ForeignKey('items.id'))
    item = relationship('Item', back_populates='bids')

    def to_dict(self):
        return {
            "username": self.bidder.username,
            "time": self.time,
            "amount": self.amount,
            "time": self.time
        }

class Comment(Base):
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True)
    text = Column(String)
    rating = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    author_id = Column(Integer, ForeignKey('users.id'))
    author = relationship('User', back_populates='comments')

    target_user_id = Column(Integer)

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "rating": self.rating,
            "created_at": self.created_at,
            "author_id": self.author.id,
            "author_name": get_user_by_id(self.author.id).username,
            "target_id": self.target_user_id,
        }


def close_bids():
    current_time = datetime.now()
    not_closed_items = session.query(Item).filter( Item.closed == False, Item.end_time <= current_time).all()

    for item in not_closed_items:
        item.close()

    session.commit()

def start_close_items( minutes ):
    print( "bid closer start" )
    while True:
        close_bids()
        sleep( minutes*60 )
        

Base.metadata.create_all(engine)

if __name__ != "__main__":
    Thread( target = start_close_items, args=(1,) ).start()