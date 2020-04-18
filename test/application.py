import os
import sys
import io
import csv
import boto3
from boto3.dynamodb.conditions import Key, Attr
from flask import Flask, Response, render_template, flash, session, request, redirect, url_for
from flask_session import Session
from application import create_app, db
from flask.ext.script import Manager, Shell
from utils import *
import json
import decimals

# application = Flask(__name__)
application = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(application)
TABLE_NAME = "customer"
dynamodb_client = boto3.client('dynamodb', region_name="us-west-2")
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
#dynamodb_resource.Table('customer')

@application.route("/")
def startPage():
	return render_template('base.html')

@application.route("/test")
def testPage():	
	print(dynamodb)
	response = dynamodb_client.query(
		TableName='customer',
		KeyConditionExpression='customer_id = :customer_id',
		ExpressionAttributeValues = {
			':customer_id': {'S': '0e37d916-f960-4772-a25a-01b762b5c1bd'}
		}
	)
	#itemList = json.dumps(response['Items'][0])
	print(json.dumps(response['Items']))

	return (json.dumps(response['Items']))

if __name__ == '__main__':
    application.run(host='127.0.0.1', port=8080, debug=True)