import os
import sys
import io
import csv
import boto3
from boto3.dynamodb.conditions import Key, Attr
from flask import Flask, Response, render_template, flash, session, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
from utils import *
import json
import restaurant
import uuid
import decimal
from decimal import Decimal


application = Flask(__name__)
application.register_blueprint(restaurant.bp)

TABLE_NAME = "customer"
dynamodb_client = boto3.client('dynamodb', region_name="us-west-2")
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

# random string generator to encrypt the cookie
SECRET_KEY = os.urandom(32)
application.config['SECRET_KEY'] = SECRET_KEY

# Configure session to use filesystem
application.config["SESSION_PERMANENT"] = False
application.config["SESSION_TYPE"] = "filesystem"
Session(application)


@application.route("/")
@application.route("/index")
@check_user_login
def index(customer_username, customer_id):
    table = dynamodb.Table('restaurant') # pylint: disable=no-member
    response = table.scan(
        ProjectionExpression='restaurant_id, restaurant_name'
    )

    return render_template('index.html', customer_username=customer_username, customer_id=customer_id, restaurant=response['Items'])

@application.route("/menu", methods=['GET', 'POST'])
def menuPage():
    table=dynamodb.Table('menu')
    response = table.scan(
        FilterExpression=Attr('menu_id').eq('menu_1')
    )
    data = json.dumps(response['Items'], cls=DecimalEncoder)
    if request.method == 'GET':
        return render_template('menu.html', data=data)

    if request.method == 'POST':
        menu_item_id = request.form['menu_item_id']
        print(menu_item_id)
        return render_template('menu.html', data=data)


@application.route('/restaurant/<restaurant_id>', methods=['POST'])
@check_user_login
def restaurantViews(customer_username, customer_id, restaurant_id):

    # get restaurant name
    restaurant_table=dynamodb.Table('restaurant') 
    restaurant_data = restaurant_table.scan(
        FilterExpression=Attr('restaurant_id').eq(restaurant_id)
    )
    restaurant_name = restaurant_data['Items'][0]['restaurant_name']

    # get menu id
    menu_table=dynamodb.Table('menu') 
    response = menu_table.scan(
        FilterExpression=Attr('restaurant_id').eq(restaurant_id)
    )
    menu_id = response['Items'][0]['menu_id']

    # get menu items
    menu_item_table=dynamodb.Table('menu_item')
    response = menu_item_table.scan(
        FilterExpression=Attr('menu_id').eq(menu_id)
    )
    
    menu_data = json.dumps(response['Items'], cls=DecimalEncoder)
    
    """ Route for restaurant views page """
    restaurant_id = request.form['restaurant_id']
   

    return render_template('restaurant.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, restaurant_name=restaurant_name,menu_data=menu_data)



@application.route('/login', methods=['GET', 'POST'])
@check_user_login
def login(customer_username, customer_id):
    """ Route for users login """

    if customer_username:
        return redirect(url_for('index'))

    if request.method == 'POST':
        customer_username = request.form['username']
        pw = request.form['password']

        # Get customer_id and password matching the username entered
        table = dynamodb.Table('customer') # pylint: disable=no-member
        row = table.scan(
            FilterExpression=Attr('customer_username').eq(customer_username)
        )

        # If no such username is found
        if row['Count'] == 0:
            flash("Please Enter a valid username", "danger")
            return render_template('login.html')

        # Verify password
        elif check_password_hash(row['Items'][0]['password'], pw):
            session['customer_id'] = row['Items'][0]['customer_id']
            session['customer_username'] = customer_username
            return redirect(url_for('index'))

        # If incorrect password
        else:
            flash("Please Enter a valid password", "danger")
            return render_template('login.html')

    return render_template('login.html')


@application.route('/signup', methods=['GET', 'POST'])
@check_user_login
def signup(customer_username, customer_id):
    """ Route for user registration """
    if customer_username:
        flash("Please logout First", "danger")
        return render_template('signup.html')

    table = dynamodb.Table('customer') # pylint: disable=no-member

    if request.method == 'POST':
        # get user input
        customer_username = request.form['username']
        hashed_pw = generate_password_hash(request.form['password'])
        customer_fname = request.form['customer_fname']
        customer_lname = request.form['customer_lname']
        customer_phone_num = request.form['customer_phone_num']
        customer_address_1 = request.form['customer_address_1']
        customer_address_2 = request.form['customer_address_2']
        customer_city = request.form['customer_city']
        customer_state = request.form['customer_state']
        customer_zip = request.form['customer_zip']

        # validate user input
        if not customer_username or not hashed_pw:
            flash("Please enter a valid username and password", "danger")
            return render_template('signup.html')

        # Check if username already exists
        result = table.scan(
            FilterExpression=Attr('customer_username').eq(customer_username)
        )

        if result['Count'] != 0:
            flash("The username already exists. Please enter another username.", "danger")
            return render_template('signup.html')

        # generate random UUID for customer_id
        new_customer_id_inital = uuid.uuid4()
        new_customer_id = str(new_customer_id_inital)

        # New customer input info
        item = {
            'customer_id': new_customer_id,
            'customer_username': customer_username,
            'password': hashed_pw,
            'customer_fname': customer_fname,
            'customer_lname': customer_lname,
            'customer_phone_num': customer_phone_num,
            'customer_address_1': customer_address_1,
            'customer_address_2': customer_address_2,
            'customer_city': customer_city,
            'customer_state': customer_state,
            'customer_zip': customer_zip
        }

        # if valid input, insert into users table in the db
        response = table.put_item(
            Item=item
        )

        flash("Successfully signed up! Please log in to continue", "success")
        return redirect(url_for('login'))

    return render_template('signup.html', customer_username=None)


@application.route('/logout')
def logout():
    """ Route for user logout """
    session.pop('customer_username', None)
    session.pop('customer_id', None)
    return redirect(url_for('index'))

class DecimalEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

if __name__ == '__main__':
    application.run(host='127.0.0.1', port=8080, debug=True)