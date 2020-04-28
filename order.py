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

bp = Blueprint('order', __name__, url_prefix='/order')


@bp.route('/<restaurant_id>', methods=['GET','POST'])
@check_user_login
def get_order(customer_username, customer_id, restaurant_id):

    # generate order_id
    order_id = str(uuid.uuid4())
    
    menu_items = request.form.getlist('menu_item_id')
    print("List of menu items: " + str(menu_items))


    item_quantity = list(map(int, request.form.getlist('menu_item')))
    print("List of item quantities: " + str(item_quantity))

    #get the current time and convert it into a string
    named_tuple = time.localtime() # get struct_time
    time_string = time.strftime("%m/%d/%Y, %H:%M:%S", named_tuple)

    res = dict(zip(menu_items, item_quantity))
    print(res)
    for key in list(res):
        if res[key] == 0:
            del res[key]
    print(res)

    order = dict(menu_items=res)

    order['order_time'] = time_string
    order['order_id'] = order_id
    order['order_type'] = None
    order['order_fulfilled_time'] = None
    order['order_status'] = None
    order['customer_id'] = customer_id
    order['restaurant_id'] = restaurant_id
    order['table_id'] = None
    print(order)

    #convert the string back into time
    #string_to_time = time.strptime(time_string, "%m/%d/%Y, %H:%M:%S")
    #print(string_to_time)

    return render_template('order.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, order=order)
    
    # # get restaurant name
    # restaurant_table=dynamodb.Table('restaurant') 
    # restaurant_data = restaurant_table.scan(
    #     FilterExpression=Attr('restaurant_id').eq(restaurant_id)
    # )
    # restaurant_name = restaurant_data['Items'][0]['restaurant_name']

    # # get menu id
    # menu_table=dynamodb.Table('menu') 
    # response = menu_table.scan(
    #     FilterExpression=Attr('restaurant_id').eq(restaurant_id)
    # )
    # menu_id = response['Items'][0]['menu_id']

    # # get menu items
    # menu_item_table=dynamodb.Table('menu_item')
    # response = menu_item_table.scan(
    #     FilterExpression=Attr('menu_id').eq(menu_id)
    # )
    
    # menu_data = json.dumps(response['Items'], cls=DecimalEncoder)

    # if request.method == 'GET':

    #     return render_template('restaurant.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, restaurant_name=restaurant_name,menu_data=menu_data)

    # if request.method == 'POST':
    #     menu_item_id = request.form['menu_item_id']



