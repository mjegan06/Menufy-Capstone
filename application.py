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
import restuarant
import uuid
import decimal
from decimal import Decimal


application = Flask(__name__)
application.register_blueprint(restuarant.bp)

TABLE_NAME = "customer"
dynamodb_client = boto3.client('dynamodb', region_name="us-west-2")
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('customer') # pylint: disable=no-member

# random string generator to encrypt the cookie
SECRET_KEY = os.urandom(32)
application.config['SECRET_KEY'] = SECRET_KEY

# Configure session to use filesystem
application.config["SESSION_PERMANENT"] = False
application.config["SESSION_TYPE"] = "filesystem"
Session(application)


@application.route("/")
@application.route("/index")
def startPage():
    print(dynamodb)
    response = dynamodb_client.query(
        TableName='customer',
        KeyConditionExpression='customer_id = :customer_id',
        ExpressionAttributeValues = {
            ':customer_id': {'S': '0e37d916-f960-4772-a25a-01b762b5c1bd'}
        }
    )
    #itemList = json.dumps(response['Items'][0])
    # print(json.dumps(response['Items']))
    
    return (json.dumps(response['Items']))

@application.route("/menu")
def menuPage():
    table=dynamodb.Table('menu_item')
    response = table.scan(
        FilterExpression=Attr('menu_id').eq('menu_1')
    )
    data = json.dumps(response['Items'], cls=DecimalEncoder)

    return render_template('menu.html', data=data)

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
        table = dynamodb.Table('customer')
        row = table.query(
            ProjectionExpression="#customer_username",
            ExpressionAttributeValues = {"#customer_username": "customer_username"},
            KeyConditionExpression=Key('customer_username').eq(customer_username),
        )

        # If no such username is found
        if not row:
            flash("Please Enter a valid username", "danger")
            return render_template('login.html')

        # Verify password
        elif check_password_hash(row['password'], pw):
            session['customer_id'] = row['customer_id']
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

    table = dynamodb.Table('customer')

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

        print(result)

        if result['Count'] != 0:
            flash("The username already exists. Please enter another username.", "danger")
            return render_template('signup.html')

        # generate random UUID for customer_id
        new_customer_id_inital = uuid.uuid4()
        new_customer_id = str(new_customer_id_inital)

        # if valid input, insert into users table in the db
        response = table.put_item(
            Item={
                'customer_id':{'S':new_customer_id},
                'customer_username':{'S':customer_username},
                'password':{'S':hashed_pw},
                'customer_fname':{'S':customer_fname},
                'customer_lname': {'S':customer_lname},
                'customer_phone_num': {'S':customer_phone_num},
                'customer_address_1': {'S':customer_address_1},
                'customer_address_2': {'S':customer_address_2},
                'customer_city': {'S':customer_city},
                'customer_state': {'S':customer_state},
                'customer_zip': {'S':customer_zip}
            }
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
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

if __name__ == '__main__':
    application.run(host='127.0.0.1', port=8080, debug=True)