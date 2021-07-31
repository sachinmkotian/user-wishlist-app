from flask import Flask, render_template, request
import redis
import os


app = Flask(__name__)

POSTGRES_USER = os.environ['POSTGRES_USER']
POSTGRES_PASSWORD = os.environ['POSTGRES_PASSWORD']
POSTGRES_DB = os.environ['POSTGRES_DB']
POSTGRES_HOST = os.environ['POSTGRES_HOST']
POSTGRES_PORT = os.environ['POSTGRES_PORT']
REDIS_PORT = os.environ['REDIS_PORT']
REDIS_HOST = os.environ['REDIS_HOST']

# postgresql://username:password@host:post/database
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'

from models import db,UserFavs

db.init_app(app)
with app.app_context():
    db.create_all()
    db.session.commit()

red = redis.Redis(host=REDIS_HOST,port=REDIS_PORT)

@app.route("/")
def main():
    return render_template("index.html")

@app.route("/save",methods=['POST'])
def save():
    username = request.form['username']
    place=request.form['place']
    food=request.form['food']

    print("username:",username)
    print("place:",place)
    print("food:",food)

    # Check if username exists in redis
    if red.hgetall(username).keys():
        print("hget username:",red.hgetall(username))
        return render_template('index.html',user_exists=1,msg='(From redis)',username=username,place=red.hget(username,"place").decode('utf-8'),food=red.hget(username,"food").decode('utf-8'))
    #if not in redis check in db
    elif len(list(red.hgetall(username).keys())) == 0:
        record = UserFavs.query.filter_by(username=username).first()
        print("Records fetched from db:", record)

        if record:
            red.hset(username,"place",record.place)
            red.hset(username,"food",record.food)            

            return render_template('index.html',user_exists=1,msg='(From DataBase)',username=username,place=record.place,food=record.food)

    # if data of the username doesn't exists either in redis or in db
    # create a new record into db and store the data in redis as well
    
    new_record = UserFavs(username=username,place=place,food=food)
    db.session.add(new_record)
    db.session.commit()

    red.hset(username,"place",place)
    red.hset(username,"food",food)

    #check if data inserted in db correctly
    record = UserFavs.query.filter_by(username=username).first()
    print("Records fetched from db:", record)

    #check if data inserted in redis correctly
    print("username from redi: ",red.hgetall(username))

    return render_template('index.html',saved=1,msg='(created new record and saved in redis)',username=username,place=red.hget(username,"place").decode('utf-8'),food=red.hget(username,"food").decode('utf-8'))


@app.route ("/keys",methods=['GET'])    
def keys():
    records=UserFavs.query.all()
    names=[]
    for record in records:
        names.append(record.username)
    return render_template('index.html',keys=1,usernames=names)

@app.route ("/get",methods=['POST'])    
def get():
    username = request.form["username"]
    print("username for get method:",username)
    user_data=red.hgetall(username)
    if not user_data:
        record = UserFavs.query.filter_by(username=username).first()
        if not record:
            return render_template('index.html',no_record=1,msg=f"Record not defined for {username}")
        
        red.hset(username,"place",record.place)
        red.hset(username,"food",record.food)
        return render_template('index.html',get=1,msg='(From DataBase)',username=username,place=record.place,food=record.food)
    return render_template('index.html',get=1,msg='(From redis)',username=username,place=red.hget(username,"place").decode('utf-8'),food=red.hget(username,"food").decode('utf-8'))


