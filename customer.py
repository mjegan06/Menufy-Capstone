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


            restaurant_id=""

            for item in order_data['Items']:
                for key, value in item.items():
                    if key == "restaurant_id":
                        restaurant_id = value
                        restaurant_data = restaurant_table.query(
                            KeyConditionExpression=Key('restaurant_id').eq(restaurant_id)
                        )
                item['restaurant_name']=restaurant_data['Items'][0]['restaurant_name']
        


            return render_template('customer_dashboard.html', customer_username=customer_username, customer_id=customer_id, customer_info=customer_data, orders=order_data)

        elif order_date and not end_date:
            order_date_time=""

            if order_time:
                order_date_time = "%s, %s" % (order_date, order_time)
            else:
                order_date_time = "%s, %s" % (order_date, "00:00:00")



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


        return render_template('customer_dashboard.html', customer_username=customer_username, customer_id=customer_id, customer_info=customer_data, orders=order_data)

@bp.route('/<restaurant_id>/<order_id>', methods=['GET'])
def get_order_details( restaurant_id, order_id):

    order_table=dynamodb.Table('order')

    order_data = order_table.query(
        KeyConditionExpression=Key('order_id').eq(order_id)
    )

    try:
        #dynamodb tables
        menu_table=dynamodb.Table('menu_item')
        order_item_table=dynamodb.Table('order_item')

        #declare variables
        oi_id = order_data['Items'][0]['oi_id']
        food_list = []

        for each in oi_id:
            #query order_items to get the item_id, quantity and unit_price
            oi_data = order_item_table.query(
                KeyConditionExpression=Key('order_item_id').eq(each)
            )
            #query menu table for the item_name and item_unit price
            menu_data = menu_table.query(
                KeyConditionExpression=Key('menu_item_id').eq(oi_data['Items'][0]['item_id'])
            )

            #To display in order review
            item_name = menu_data['Items'][0]['item_name']
            oi_quantity = oi_data['Items'][0]['oi_quantity']
            item_unit_price = menu_data['Items'][0]['item_unit_price']
            oi_unit_price = oi_data['Items'][0]['oi_unit_price']

            order_details = {
                'item_name': item_name,
                'oi_quantity': oi_quantity,
                'item_unit_price': item_unit_price,
                'oi_unit_price': oi_unit_price
            }
            food_list.append(order_details)

        order_total = order_data['Items'][0]['order_total']
        food_list.append({'order_total': order_total})
        food_list = json.dumps(food_list, cls=DecimalEncoder)
        
        return (food_list)
    
    except:
        return ("")

