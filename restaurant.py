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
table = dynamodb.Table('restaurant') # pylint: disable=no-member

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

bp = Blueprint('restaurant', __name__, url_prefix='/restaurant')


# Get restaurant information
@bp.route('/<restaurant_id>', methods=['GET','POST'])
@check_user_login
def get_restaurant(customer_username, customer_id, restaurant_id):
    # get restaurant name
    restaurant_table=dynamodb.Table('restaurant') # pylint: disable=no-member
    restaurant_data = restaurant_table.scan(
        FilterExpression=Attr('restaurant_id').eq(restaurant_id)
    )
    restaurant_name = restaurant_data['Items'][0]['restaurant_name']

    # get menu id
    menu_table=dynamodb.Table('menu') # pylint: disable=no-member
    response = menu_table.scan(
        FilterExpression=Attr('restaurant_id').eq(restaurant_id)
    )
    menu_id = response['Items'][0]['menu_id']

    # get menu items
    menu_item_table=dynamodb.Table('menu_item') # pylint: disable=no-member
    response = menu_item_table.scan(
        FilterExpression=Attr('menu_id').eq(menu_id)
    )
    
    menu_object = {}
    for x in response['Items']:
        # for displaying by item_type, if the item_type isn't in the dict, then create a new item_type to display
        if x['item_type'] not in menu_object:
            menu_object[x['item_type']] = [{
            'menu_item_id': x['menu_item_id'],
            'item_name': x['item_name'],
            'item_description': x['item_description'],
            'item_unit_price': str(x['item_unit_price'])
            }]
        else:
            menu_object[x['item_type']].append(
                {
            'menu_item_id': x['menu_item_id'],
            'item_name': x['item_name'],
            'item_description': x['item_description'],
            'item_unit_price': str(x['item_unit_price'])
            }
            )


    if request.method == 'GET':

        return render_template('restaurant.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, restaurant_name=restaurant_name, new_menu=menu_object)




