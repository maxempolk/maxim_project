from flask import Flask, jsonify, request
from flask_cors import CORS
from json import loads
import datetime
from time import sleep
from db import get_items, items_to_dict, get_item_by_id, create_user, check_password, get_user_by_name, create_bid, create_item, Bid, get_user_by_id, get_comments_about_user, create_coment_db
from validators import *
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
import os
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)

# app.config['SECRET_KEY'] = 'aoaooaao'
app.config["JWT_SECRET_KEY"] = "abobus"  
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies", "json", "query_string"]

jwt = JWTManager(app)

CORS(app)

PUBLIC_DIR_PATH = "../frontend/public/"

def count_files_in_directory():
    try:
        files = os.listdir(PUBLIC_DIR_PATH)
        files = [file for file in files if os.path.isfile(os.path.join(PUBLIC_DIR_PATH, file))]
        file_count = len(files)
        return file_count
    except OSError as e:
        print(f"Ошибка: {e}")
        return None

def create_image_by_base64( base64_image, default_path = PUBLIC_DIR_PATH ):
    DEFAULT_EXTENTION = "png"
    try:
        file_name = count_files_in_directory()
        full_path = f"{default_path}/{file_name}.{DEFAULT_EXTENTION}"
        
        base64_data = base64_image.split(",")[1]
        image_data = base64.b64decode(base64_data)
        image_buffer = BytesIO(image_data)
        image = Image.open(image_buffer)
        image.save(full_path)

        return full_path
    except Exception as exp:
        return False

def error( message, **args ):
    return jsonify({"ok": False, "message": message, **args})

@app.route("/get_lots", methods=["post"])
def get_lots():
    return jsonify( items_to_dict(get_items()) )

@app.route("/search_lot_by_row", methods=["post"])
def search_lot_by_row():
    data = request.get_json()
    rows = data.get("row", None).split()
    # check error
    items = get_items()
    for row in rows:
        row = row.lower().strip()
        items = list(filter( 
            lambda item: 
                row in item.title.lower().strip() or 
                row in item.owner.username.lower().strip(),
            items
        ))
    return jsonify(items_to_dict(items))

@app.route( "/get_item", methods=["post"] )
def get_item():
    data = request.get_json()
    id = data.get("id", None)
    return jsonify({"item": get_item_by_id( id ).to_dict()})

@app.route( "/get_user", methods=["post"] )
def get_user():
    data = request.get_json()
    id = data.get("id", None)

    user = get_user_by_id( id )

    if user:
        return jsonify( {"user": user.to_dict()} )
    return error("Something going bad")


@app.route( "/register", methods=["post"] )
def register():
    data = request.get_json()
    username = data.get( "username", None )
    email = data.get( "email", None )
    password = data.get( "password", None )

    if not (username and email and password):
        return error("User input is invalid")

    user_create_result = create_user( username, email, password )
    if not user_create_result:
        return error("Something going bad. Maybe user with your email or username already created")

    access_token = create_access_token(identity=username, expires_delta=datetime.timedelta(days=1))
    return jsonify( access_token=access_token )

@app.route( "/login", methods=["post"] )
def login():
    data = request.get_json()
    username = data.get( "username", None )
    password = data.get( "password", None )
    if not (username and password):
        return error("User input is invalid")
    
    if check_password(data["username"], data["password"]):
        access_token = create_access_token(identity=username, expires_delta=datetime.timedelta(days=1))
        return jsonify( access_token=access_token )
    else:
        return error("Invalid password or user name. Recheck the data and try again")

@app.route( "/get_user_info", methods=["post"] )
@jwt_required()
def get_user_info():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

@app.route( "/do_bid", methods=["post"] )
@jwt_required()
def do_bid():
    data = request.json
    username = get_jwt_identity()
    among = data.get("among", None)
    item_id = data.get("item_id", None)
    
    if not (username and among and item_id):
        return error("User input is invalid")
    
    user = get_user_by_name( username )
    item = get_item_by_id( item_id )

    if user == get_user_by_id(item.owner_id):
        return error( "You cant do bid to yourself item)))" )

    if not user or not item:
        return error("User input is invalid")
    
    if datetime.datetime.now() > item.end_time:
        return error("The date has already passed", is_end = True)

    created_bid = create_bid( username, among, item_id )

    if not created_bid:
        return error("User input is invalid")

    return jsonify({"ok": True})

@app.route( "/create_item", methods=["post"] )
@jwt_required()
def create_item_func():
    data = request.json
    username = get_jwt_identity()
    title = data.get("title", None)
    description = data.get("description", None)
    starting_price = data.get("starting_price", None)
    bid_increment = data.get("bid_increment", None)
    end_time = data.get("end_time", None)
    covers_files = data.get("covers_files", None)

    if not (username and title and description and starting_price and bid_increment and end_time and covers_files):
        return error("User input is invalid")
    
    local_images = []
    for base64 in covers_files:
        local_path = create_image_by_base64( base64 )
        file_name = local_path.split("/")[-1]
        local_images.append( file_name )

    res = create_item( username, title, description, starting_price, bid_increment, end_time, local_images )
    
    if res:
        return jsonify({"ok": True})
    
    return jsonify({"ok": False})

@app.route( "/get_comments", methods=["post"] )
def get_comments():
    data = request.json

    user_id = data.get( "user_id", None )
    if user_id == None:
        return error( "No comments" )
    
    comments = get_comments_about_user( user_id )
    comments_formated = list(map( lambda comment: comment.to_dict(), comments ))
    return jsonify( comments_formated )

@app.route( "/create_coment", methods=["post"] )
@jwt_required()
def create_coment():
    data = request.json
    username = get_jwt_identity()

    user = get_user_by_name( username )
    if not user:
        return error("User input is invalid")

    text = data.get( "text", None )
    rating = data.get( "rating", None )
    author_id = user.id
    seller_id = data.get( "owner_id", None )
    
    print( text, rating, author_id, seller_id )
    if not(text and rating and author_id and seller_id):
        return error("User input is invalid")

    res = create_coment_db( text, rating, author_id, seller_id )
    print( res )
    if res:
        print( "created" )
        return jsonify({"status": 200, "ok": True})
    return error("Something going bad.")

# def create_comment( text, rating, author_id, seller_id ):
