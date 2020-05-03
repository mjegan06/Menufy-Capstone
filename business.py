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

bp = Blueprint('business', __name__, url_prefix='/business')


@bp.route('/<rid>/home', methods=['GET'])
@business_check_user_login
def business_home(restaurant_username, restaurant_id, rid):
    table = dynamodb.Table('restaurant') # pylint: disable=no-member
    row = table.scan(
        FilterExpression=Attr('restaurant_username').eq(restaurant_username)
    )

    restaurant_name = row['Items'][0]['restaurant_name']

    return render_template('business_home.html', restaurant_name = restaurant_name, restaurant_username=restaurant_username, restaurant_id=restaurant_id)


@bp.route('/<rid>/orders', methods=['GET'])
@business_check_user_login
def business_orders(restaurant_username, restaurant_id, rid):
    table = dynamodb.Table('restaurant') # pylint: disable=no-member
    row = table.scan(
        FilterExpression=Attr('restaurant_username').eq(restaurant_username)
    )

    restaurant_name = row['Items'][0]['restaurant_name']

    return render_template('business_orders.html', restaurant_name = restaurant_name, restaurant_username=restaurant_username, restaurant_id=restaurant_id)

@bp.route('/<rid>/inventory', methods=['GET'])
@business_check_user_login
def business_inventory(restaurant_username, restaurant_id, rid):
    table = dynamodb.Table('restaurant') # pylint: disable=no-member
    row = table.scan(
        FilterExpression=Attr('restaurant_username').eq(restaurant_username)
    )

    restaurant_name = row['Items'][0]['restaurant_name']

    return render_template('business_inventory.html', restaurant_name = restaurant_name, restaurant_username=restaurant_username, restaurant_id=restaurant_id)
