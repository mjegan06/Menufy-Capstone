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
import decimal
from decimal import Decimal


application = Flask(__name__)
application.register_blueprint(restuarant.bp)

TABLE_NAME = "customer"
dynamodb_client = boto3.client('dynamodb', region_name="us-west-2")
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('customer') # pylint: disable=no-member


@application.route("/")
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
    print(data)

    return render_template('menu.html', data=data)

@application.route('/login', methods=['GET', 'POST'])
@check_user_login
def login(username, user_id):
    """ Route for users login """

    if username:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        pw = request.form['password']

        # Get user_id and password matching the username entered
        table = dynamodb.Table('customer')
        row = table.query(
            ProjectionExpression="#username",
            ExpressionAttributeValues = {"#username": "username"},
            KeyConditionExpression=Key('username').eq(username),
        )

        # If no such username is found
        if not row:
            flash("Please Enter a valid username", "danger")
            return render_template('login.html')

        # Verify password
        elif check_password_hash(row['password'], pw):
            session['customer_id'] = row['customer_id']
            session['user'] = username
            return redirect(url_for('index'))

        # If incorrect password
        else:
            flash("Please Enter a valid password", "danger")
            return render_template('login.html')

    return render_template('login.html')


@application.route('/signup', methods=['GET', 'POST'])
@check_user_login
def signup(username, user_id):
    """ Route for user registration """
    if username:
        flash("Please logout First", "danger")
        return render_template('signup.html')

    if request.method == 'POST':
        # get user input
        username = request.form['username']
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
        if not username or not hashed_pw:
            flash("Please enter a valid username and password", "danger")
            return render_template('signup.html')

        # Check if username already exists
        table = dynamodb.Table('customer')
        result = table.query(
            ProjectionExpression="#username",
            ExpressionAttributeValues = {"#username": "username"},
            KeyConditionExpression=Key('username').eq(username),
        )

        if result:
            flash("The username already exists. Please enter another username.", "danger")
            return render_template('signup.html')

        # if valid input, insert into users table in the db
        response = table.put_item(
            Item={
                'username': username,
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
        )

        flash("Successfully signed up! Please log in to continue", "success")
        return redirect(url_for('login'))

    return render_template('signup.html', username=None)


@application.route('/logout')
def logout():
    """ Route for user logout """
    session.pop('user', None)
    session.pop('user_id', None)
    return redirect(url_for('index'))

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

if __name__ == '__main__':
    application.run(host='127.0.0.1', port=8080, debug=True)