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
import time
import json
import uuid
import decimal
from decimal import Decimal
import restaurant
import order as o
#from order import bluep
import random
import business
import customer
from flask_mail import Mail, Message


application = Flask(__name__)

application.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME = 'menufy.capstone@gmail.com',
    MAIL_PASSWORD = 'Capstone20!'
)
mail = Mail(application)

application.register_blueprint(restaurant.bp)
application.register_blueprint(o.bp)
application.register_blueprint(business.bp)
application.register_blueprint(customer.bp)

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
    table = dynamodb.Table('restaurant')  # pylint: disable=no-member
    response = table.scan(
        ProjectionExpression='restaurant_id, restaurant_name'
    )

    return render_template('index.html', customer_username=customer_username, customer_id=customer_id, restaurant=response['Items'])


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
        flash("Please logout first", "danger")
        return render_template('signup.html')

    table = dynamodb.Table('customer') # pylint: disable=no-member

    if request.method == 'POST':
        # get user input
        customer_username = request.form['username']
        customer_email = request.form['customer_email']
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
            'customer_email': customer_email,
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


##########################        business login routes        #######################

@application.route('/business_login', methods=['GET', 'POST'])
@business_check_user_login
def business_login(restaurant_username, restaurant_id):
    """ Route for business login """

    if restaurant_username:
        return redirect(url_for('business.business_home', rid = restaurant_id))

    if request.method == 'POST':
        restaurant_username = request.form['username']
        pw = request.form['password']

        # Get restaurant_id and password matching the username entered
        table = dynamodb.Table('restaurant') # pylint: disable=no-member
        row = table.scan(
            FilterExpression=Attr('restaurant_username').eq(restaurant_username)
        )

        # If no such username is found
        if row['Count'] == 0:
            flash("Please Enter a valid username", "danger")
            return render_template('business_login.html')

        # Verify password
        elif check_password_hash(row['Items'][0]['password'], pw):
            session['restaurant_id'] = row['Items'][0]['restaurant_id']
            restaurant_id =  row['Items'][0]['restaurant_id']
            session['restaurant_username'] = restaurant_username
            return redirect(url_for('business.business_home', rid = restaurant_id))

        # If incorrect password
        else:
            flash("Please Enter a valid password", "danger")
            return render_template('business_login.html')

    return render_template('business_login.html')


@application.route('/business_signup', methods=['GET', 'POST'])
@business_check_user_login
def business_signup(restaurant_username, restaurant_id):
    """ Route for user registration """
    if restaurant_username:
        flash("Please logout first", "danger")
        return render_template('business_signup.html')

    table = dynamodb.Table('restaurant') # pylint: disable=no-member

    if request.method == 'POST':
        # get user input
        restaurant_username = request.form['username']
        hashed_pw = generate_password_hash(request.form['password'])
        restaurant_email = request.form['restaurant_email']
        restaurant_name = request.form['restaurant_name']
        restaurant_phone_num = request.form['restaurant_phone_num']
        restaurant_address_1 = request.form['restaurant_address_line1']
        restaurant_address_2 = request.form['restaurant_address_line2']
        restaurant_city = request.form['restaurant_city']
        restaurant_state = request.form['restaurant_state']
        restaurant_postal_code = request.form['restaurant_postal_code']

        # validate user input
        if not restaurant_username or not hashed_pw:
            flash("Please enter a valid username and password", "danger")
            return render_template('business_signup.html')

        # Check if username already exists
        result = table.scan(
            FilterExpression=Attr('restaurant_username').eq(restaurant_username)
        )

        if result['Count'] != 0:
            flash("The username already exists. Please enter another username.", "danger")
            return render_template('business_signup.html')

        # generate random UUID for restaurant_id
        new_restaurant_id_inital = uuid.uuid4()
        new_restaurant_id = str(new_restaurant_id_inital)

        # New customer input info
        item = {
            'restaurant_id': new_restaurant_id,
            'restaurant_username': restaurant_username,
            'password': hashed_pw,
            'restaurant_email': restaurant_email,
            'restaurant_name': restaurant_name,
            'restaurant_phone_num': restaurant_phone_num,
            'restaurant_address_line1': restaurant_address_1,
            'restaurant_address_line2': restaurant_address_2,
            'restaurant_city': restaurant_city,
            'restaurant_state': restaurant_state,
            'restaurant_postal_code': restaurant_postal_code
        }

        # if valid input, insert into users table in the db
        table.put_item(
            Item=item
        )

        menu_table = dynamodb.Table('menu') # pylint: disable=no-member

        # generate random UUID for restaurant_id
        new_menu_id_inital = uuid.uuid4()
        new_menu_id = str(new_restaurant_id_inital)

        item = {
            'restaurant_id': new_restaurant_id,
            'menu_id': new_menu_id
        }

        menu_table.put_item(
            Item=item
        )


        flash("Successfully signed up! Please log in to continue", "success")
        return redirect(url_for('business_login'))

    return render_template('business_signup.html', restaurant_username=None)


@application.route('/business_logout')
def business_logout():
    """ Route for business logout """
    session.pop('restaurant_username', None)
    session.pop('restaurant_id', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    port = random.randint(5000,8999)
    application.run(host='127.0.0.1', port=port, debug=True)
