import os
import sys
import io
import csv
import boto3
from boto3.dynamodb.conditions import Key, Attr
from flask import Flask, Blueprint, request, make_response, flash, Response, render_template,  session, redirect, url_for
from flask_session import Session
from utils import *
import time
import json
import decimal
import uuid

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
# table = dynamodb.Table('restaurant') # pylint: disable=no-member

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

bp = Blueprint('customer', __name__, url_prefix='/customer')

###################################################################

@bp.route('/<cid>/dashboard', methods=['GET','POST'])
@check_user_login
def customer_dashboard(customer_username, customer_id, cid):

    if cid != customer_id:
        error = "Unable to look at another customer's dashboard, please sign in if you haven't done so already"
        flash(u'Unable to access dashboard, please login to your account', 'error')
        return redirect(url_for('login'))

    customer_table=dynamodb.Table('customer')
    restaurant_table=dynamodb.Table('restaurant')
    order_table=dynamodb.Table('order')

    customer_data = customer_table.query(
        KeyConditionExpression=Key('customer_id').eq(customer_id)
    )
    customer_data['Items'][0]['password'] = None

    if request.method == 'POST':
        order_date = request.form['order_date'] if request.form['order_date'] else None
        order_time = request.form['order_time'] if request.form['order_time'] else None
        end_date = request.form['end_date'] if request.form['end_date'] else None
        end_time = request.form['end_time'] if request.form['end_time'] else None

        if order_date and end_date:
            order_date_time=""
            end_date_time=""

            if order_time:
                order_date_time = "%s, %s" % (order_date, order_time)
            else:
                order_date_time = "%s, %s" % (order_date, "00:00:00")
            
            if end_time:
                end_date_time = "%s, %s" % (end_date, end_time)
            else:
                end_date_time = "%s, %s" % (end_date, "00:00:00")

            order_data = order_table.scan(
                FilterExpression=Key('customer_id').eq(customer_id) & Attr('order_time').between(order_date_time, end_date_time)
            )
            print(order_data)

            restaurant_id=""

            for item in order_data['Items']:
                for key, value in item.items():
                    if key == "restaurant_id":
                        restaurant_id = value
                        restaurant_data = restaurant_table.query(
                            KeyConditionExpression=Key('restaurant_id').eq(restaurant_id)
                        )
                item['restaurant_name']=restaurant_data['Items'][0]['restaurant_name']
        
            print(order_data)

            return render_template('customer_dashboard.html', customer_username=customer_username, customer_id=customer_id, customer_info=customer_data, orders=order_data)

        elif order_date and not end_date:
            order_date_time=""

            if order_time:
                order_date_time = "%s, %s" % (order_date, order_time)
            else:
                order_date_time = "%s, %s" % (order_date, "00:00:00")

            print(order_date_time)

            order_data = order_table.scan(
                FilterExpression=Attr('customer_id').eq(customer_id) & Attr('order_time').gte(order_date_time)
            )

            restaurant_id=""

            for item in order_data['Items']:
                for key, value in item.items():
                    if key == "restaurant_id":
                        restaurant_id = value
                        restaurant_data = restaurant_table.query(
                            KeyConditionExpression=Key('restaurant_id').eq(restaurant_id)
                        )
                item['restaurant_name']=restaurant_data['Items'][0]['restaurant_name']
        
            print(order_data)

            return render_template('customer_dashboard.html', customer_username=customer_username, customer_id=customer_id, customer_info=customer_data, orders=order_data)

        elif not order_date and end_date:
            end_date_time=""
            
            if end_time:
                end_date_time = "%s, %s" % (end_date, end_time)
            else:
                end_date_time = "%s, %s" % (end_date, "00:00:00")

            order_data = order_table.scan(
                FilterExpression=Attr('customer_id').eq(customer_id) & Attr('order_time').lte(end_date_time)
            )

            restaurant_id=""

            for item in order_data['Items']:
                for key, value in item.items():
                    if key == "restaurant_id":
                        restaurant_id = value
                        restaurant_data = restaurant_table.query(
                            KeyConditionExpression=Key('restaurant_id').eq(restaurant_id)
                        )
                item['restaurant_name']=restaurant_data['Items'][0]['restaurant_name']
        
            print(order_data)

            return render_template('customer_dashboard.html', customer_username=customer_username, customer_id=customer_id, customer_info=customer_data, orders=order_data)

        else:
            order_data = order_table.scan(
                FilterExpression=Attr('customer_id').eq(customer_id)
            )

            restaurant_id=""

            for item in order_data['Items']:
                for key, value in item.items():
                    if key == "restaurant_id":
                        restaurant_id = value
                        restaurant_data = restaurant_table.query(
                            KeyConditionExpression=Key('restaurant_id').eq(restaurant_id)
                        )
                item['restaurant_name']=restaurant_data['Items'][0]['restaurant_name']
        
            print(order_data)

            return render_template('customer_dashboard.html', customer_username=customer_username, customer_id=customer_id, customer_info=customer_data, orders=order_data)
    
    else:
        order_data = order_table.scan(
            FilterExpression=Attr('customer_id').eq(customer_id)
        )

        restaurant_id=""

        for item in order_data['Items']:
            for key, value in item.items():
                if key == "restaurant_id":
                    restaurant_id = value
                    restaurant_data = restaurant_table.query(
                        KeyConditionExpression=Key('restaurant_id').eq(restaurant_id)
                    )
            item['restaurant_name']=restaurant_data['Items'][0]['restaurant_name']
        
        print(customer_username)
        print(customer_id)
        print(customer_data)
        print(order_data)

        return render_template('customer_dashboard.html', customer_username=customer_username, customer_id=customer_id, customer_info=customer_data, orders=order_data)

