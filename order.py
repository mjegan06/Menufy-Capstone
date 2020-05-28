import os
import sys
import io
import csv
import boto3
import requests
from boto3.dynamodb.conditions import Key, Attr
from flask import Flask, Blueprint, request, make_response, flash, Response, render_template,  session, redirect, url_for
from flask_session import Session
from utils import *
import time
import json
import decimal
import random
import string
import uuid
from flask_mail import Mail, Message
#import application
from flask import current_app

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
# table = dynamodb.Table('restaurant') # pylint: disable=no-member

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

bp = Blueprint('order', __name__, url_prefix='/order')

tax_api_key = '2ua9Sp7sTDhfCgM4'


@bp.route('/<restaurant_id>', methods=['GET','POST'])
@check_user_login
def get_order(customer_username, customer_id, restaurant_id):
    oiTable = dynamodb.Table('order_item') # pylint: disable=no-member
    menuTable = dynamodb.Table('menu_item') # pylint: disable=no-member
    orderTable = dynamodb.Table('order') # pylint: disable=no-member
    restTable = dynamodb.Table('restaurant') # pylint: disable=no-member

    if request.method == 'POST':
        menu_items = request.form.getlist('menu_item_id')


        item_quantity = list(map(int, request.form.getlist('quantity')))

        res = dict(zip(menu_items, item_quantity))
        for key in list(res):
            if res[key] == 0:
                del res[key]

        orderSubtotal = 0
        itemDetails = []
        for key in res:
            response = menuTable.get_item(
                Key={'menu_item_id': key}
            )

            itemDetails.append({
            'item_id': key,
            'item_name': response['Item']['item_name'],
            'quantity': res[key], 
            'item_subtotal': response['Item']['item_unit_price'] * res[key]
            })
            
            orderSubtotal = orderSubtotal + int(response['Item']['item_unit_price']) * int(res[key])
            
        

        response = restTable.get_item(
            Key={'restaurant_id': restaurant_id}
            )
        restName = response['Item']['restaurant_name']
        orderDetails = dict(username = customer_username, orderSubtotal = orderSubtotal, restName = restName)
        return render_template('order_summary.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, order=orderDetails, itemDetails=itemDetails)

@bp.route('/<restaurant_id>/customer/', methods=['GET','POST'])
@check_user_login
def place_order(customer_username, customer_id, restaurant_id):

    if request.method == "POST":
        
        if not customer_id:
            print("Not logged in")
            flash("You must be logged in to place an order", "danger")
            return redirect(url_for('index'))

        oiTable = dynamodb.Table('order_item') # pylint: disable=no-member
        menuTable = dynamodb.Table('menu_item') # pylint: disable=no-member
        orderTable = dynamodb.Table('order') # pylint: disable=no-member
        restTable = dynamodb.Table('restaurant') # pylint: disable=no-member
        custTable = dynamodb.Table('customer') # pylint: disable=no-member



        
        # generate order_id
        order_id = str(uuid.uuid4())
        
        menu_items = list(request.form.getlist("item_id"))
        quantites = request.form.getlist('item_quantity')
        subtotals = request.form.getlist("item_subtotal")

        sub_order = {}


        for i in range(len(menu_items)):
            sub_order[menu_items[i]] = {'Quantity': int(quantites[i]), "subtotal": int(subtotals[i])}


        orderSubtotal = 0
        orderIdList = []
        for key in sub_order:
            orderItemId = str(uuid.uuid4())
            
            
            item = {
                    'order_id': order_id,
                    'order_item_id': orderItemId,
                    'oi_quantity': sub_order[key]['Quantity'],
                    'oi_unit_price': sub_order[key]['subtotal'],
                    'item_id': key
            }

            #update quantites of items ordered in database, subtracting items from database that were ordered
            response = menuTable.update_item(
                Key={'menu_item_id': key},
                UpdateExpression='set item_quantity_available = item_quantity_available - :val',
                ExpressionAttributeValues = {
                    ':val': item['oi_quantity']
                },
                ReturnValues = 'UPDATED_NEW'
            )
            
            #create new order_item with menu item and price
            newOrderItem = oiTable.put_item(
                Item=item
            )
            
            orderSubtotal = orderSubtotal + sub_order[key]['subtotal']
            orderIdList.append(orderItemId)
        

        #get the current time and convert it into a string
        named_tuple = time.localtime() # get struct_time
        time_string = time.strftime("%Y-%m-%d, %H:%M:%S", named_tuple)

        confirmation = "".join([random.choice(string.ascii_uppercase + string.digits) for n in range(8)])
        order = dict()

        #restrieve restaurant name, phone number, and zip code
        response = restTable.get_item(
            Key={'restaurant_id': restaurant_id}
        )
        restName = response['Item']['restaurant_name']
        restPhone = response['Item']['restaurant_phone_num']
        restZip = response['Item']['restaurant_postal_code']

        #retrieve customer email
        response = custTable.get_item(
            Key={'customer_id': customer_id}
        )
        custEmail = response['Item']['customer_email']

        #calculate sales tax for restaurant using zip-tax.com api
        tax_url = 'https://api.zip-tax.com/request/v40?key=' + tax_api_key + '&postalcode=' + str(restZip)

        tax_request = requests.get(tax_url)
        tax_request_content = json.loads(tax_request.content)
        salesTax = tax_request_content['results'][0]['taxSales']

        #calculate tax for the order
        orderTax = round(decimal.Decimal(str(salesTax * orderSubtotal)), 2)

        #calculate order total (subtotal + order tax)
        orderTotal = decimal.Decimal(str(orderTax + orderSubtotal))      



        order['order_time'] = time_string
        order['order_id'] = order_id
        order['confirmation'] = confirmation
        order['order_type'] = request.form['order_type']
        order['order_fulfilled_time'] = None
        order['order_status'] = "Submitted"
        order['customer_id'] = customer_id
        order['oi_id'] = orderIdList
        order['restaurant_id'] = restaurant_id
        order['table_id'] = None
        order['subtotal'] = orderSubtotal
        order['tax'] = orderTax
        order['order_total'] = orderTotal

        createOrder = orderTable.put_item(
        Item = order
        )

        
        orderDetails = dict(
            username = customer_username, 
            restName = restName, 
            order_time = order['order_time'],
            subtotal = orderSubtotal,
            tax =  orderTax,
            total=orderTotal, 
            confirmation=order['confirmation'],
            restPhone=restPhone)

        confirmation_url = request.url_root + 'order/?confirmation=' + confirmation
        
        
        from application import mail as mail
        try:
            msg = Message("Order Confirmation Email",
                sender = "menufy.capstone@gmail.com",
                recipients= [custEmail])
            msg.body = 'Hello ' + str(customer_username) + '\nBelow are the details of your recent order from ' + str(restName) + '\n' + 'Order Placed: ' + str(order['order_time']) + '\n' + 'Order Confirmation: ' + str(order['confirmation']) + '\n' + 'Order Subtotal: ' + str(order['order_total']) + '\n' + 'Please call ' + str(restName) + ' at ' + str(restPhone) + ' with any questions or concerns for your order.\n'
            msg.html = render_template('order_confirmation_email.html', order=orderDetails, confirmation_url=confirmation_url)
            mail.send(msg)
            confirmationMessage = "Order was successful. Confirmation email sent to " + custEmail
            flash(confirmationMessage, "success")
        except Exception as e:
            return str(e)
        return render_template('order.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, order=orderDetails, confirmation_url=confirmation_url)


@bp.route('/', methods=['GET', 'POST'])
@check_user_login
def order_status(customer_username, customer_id):
    confirmation = request.args.get('confirmation')
    if not confirmation:
        return "NO CONFIRMATION"
        
    if request.method == 'GET':
        if not customer_id:
                flash("You must be logged in to check the status of an order", "danger")
                #return redirect(url_for('index'))
                return render_template('login.html')

        orderTable = dynamodb.Table('order') # pylint: disable=no-member
        restTable = dynamodb.Table('restaurant')
        
        


        row = orderTable.scan(
            FilterExpression=Attr('confirmation').eq(confirmation)
        )
        if row['Count'] == 0:
            print("Not working")

        #restrieve restaurant name, phone number, and zip code
        response = restTable.get_item(
            Key={'restaurant_id': row['Items'][0]['restaurant_id']}
        )
        restName = response['Item']['restaurant_name']
        restPhone = response['Item']['restaurant_phone_num']
        
        
        orderDetails = dict(
            username = customer_username, 
            restName = restName, 
            order_time = row['Items'][0]['order_time'],
            status = row['Items'][0]['order_status'],
            total = row['Items'][0]['order_total'],
            restPhone=restPhone
        )
        #return 'OK'
        return render_template('order_status.html', customer_username=customer_username, customer_id=customer_id, order=orderDetails)
    else:
        return 'NOT OK'

    return "OK I'm here"



    

@bp.route('/<restaurant_id>/order_history', methods=['GET','POST'])
@check_user_login
def get_order_history(customer_username, customer_id, restaurant_id):

    restaurant_table=dynamodb.Table('restaurant')
    order_table=dynamodb.Table('order')

    restaurant_data = restaurant_table.query(
        KeyConditionExpression=Key('restaurant_id').eq(restaurant_id)
    )
    restaurant_name = restaurant_data['Items'][0]['restaurant_name']

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
                FilterExpression=Key('restaurant_id').eq(restaurant_id) & Attr('order_time').between(order_date_time, end_date_time)
            )

            for item in order_data['Items']:
                item['restaurant_name'] = restaurant_name

            return render_template('order_history.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, orders=order_data)

        elif order_date and not end_date:
            order_date_time=""

            if order_time:
                order_date_time = "%s, %s" % (order_date, order_time)
            else:
                order_date_time = "%s, %s" % (order_date, "00:00:00")

            order_data = order_table.scan(
                FilterExpression=Attr('restaurant_id').eq(restaurant_id) & Attr('order_time').gte(order_date_time)
            )

            for item in order_data['Items']:
                item['restaurant_name'] = restaurant_name

            return render_template('order_history.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, orders=order_data)

        elif not order_date and end_date:
            end_date_time=""
            
            if end_time:
                end_date_time = "%s, %s" % (end_date, end_time)
            else:
                end_date_time = "%s, %s" % (end_date, "00:00:00")

            order_data = order_table.scan(
                FilterExpression=Attr('restaurant_id').eq(restaurant_id) & Attr('order_time').lte(end_date_time)
            )

            for item in order_data['Items']:
                item['restaurant_name'] = restaurant_name

            return render_template('order_history.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, orders=order_data)

        else:
            order_data = order_table.scan(
                FilterExpression=Attr('restaurant_id').eq(restaurant_id)
            )

            for item in order_data['Items']:
                item['restaurant_name'] = restaurant_name

            return render_template('order_history.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, orders=order_data)

    order = None

    return render_template('order_history.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, orders=order)




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



