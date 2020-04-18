import os
import sys
import io
import csv
import boto3
from boto3.dynamodb.conditions import Key, Attr
from flask import Flask, Response, render_template, flash, session, request, redirect, url_for
from flask_session import Session
from utils import *
import json
import decimal

application = Flask(__name__)
dynamodb_client = boto3.client('dynamodb', region_name="us-west-2")
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

# random string generator to encrypt the cookie
SECRET_KEY = os.urandom(32)
application.config['SECRET_KEY'] = SECRET_KEY

# Configure session to use filesystem
application.config["SESSION_PERMANENT"] = False
application.config["SESSION_TYPE"] = "filesystem"
Session(application)

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

@application.route("/")
def startPage():
    table = dynamodb.Table('customer') # pylint: disable=no-member
	tableLst = []	
	response_something = table.scan()
	for i in response_something[u'Items']:
		#x = i['customer_fname'] + ' ' + i['customer_lname']
		tableLst.append(json.dumps(i, cls=DecimalEncoder))
		#print(x)
		print(json.dumps(i, cls=DecimalEncoder))
		print('\n\n')
	#rValue = response_something['Items'][0]['customer_fname'] + ' ' + response_something['Items'][0]['customer_lname']
	#print(tableLst)
	#print(response_something['Items'][0]['state'])
	#results = list(response_something['Items'])
	output = {'Item1 in database': tableLst[0]}
	print(output)
	response_zero = table.query(
		KeyConditionExpression = Key('customer_id').eq('3f0f196c-4a7b-43af-9e29-6522a715342d')
	)
	for i in response_zero['Items']:
		x = i['customer_fname'] + ' ' + i['customer_lname']
		print(x)
		print(json.dumps(x))

	print("\n\n")
	response = dynamodb_client.query(
		TableName='customer',
		KeyConditionExpression='customer_id = :customer_id',
		ExpressionAttributeValues = {
			':customer_id': {'S': '0e37d916-f960-4772-a25a-01b762b5c1bd'}
		}
	)
	
	print(json.dumps(response['Items']))
	print()

	return (json.dumps(output), {'Content-Type': 'applicationlication/json'})



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

if __name__ == '__main__':
    application.run(host='127.0.0.1', port=8080, debug=True)