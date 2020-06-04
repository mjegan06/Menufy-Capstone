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

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

bp = Blueprint('order', __name__, url_prefix='/order')

tax_api_key = '2ua9Sp7sTDhfCgM4'


#route to calculate order subtotal to display for user to review order

@bp.route('/<restaurant_id>', methods=['GET','POST'])
@check_user_login
def get_order(customer_username, customer_id, restaurant_id):

    #retrieve tables from database
    oiTable = dynamodb.Table('order_item') # pylint: disable=no-member
    menuTable = dynamodb.Table('menu_item') # pylint: disable=no-member
    orderTable = dynamodb.Table('order') # pylint: disable=no-member
    restTable = dynamodb.Table('restaurant') # pylint: disable=no-member

    if request.method == 'POST':
        #get list of menu item ids
        menu_items = request.form.getlist('menu_item_id')
        
        #make list of ints for list of quantities
        item_quantity = list(map(int, request.form.getlist('quantity')))
        
        #if user attempts to review order with zero items, redirects user to restaurant menu page
        sumQuants = 0
        for i in range(len(item_quantity)):
            
            sumQuants += item_quantity[i]
            
        if sumQuants == 0:
            return redirect(url_for('restaurant.get_restaurant', restaurant_id = restaurant_id))

        #make a dictionary pairing the menu item ids with the quantity ordered for that id
        #if quantity is zero, that menu item is removed
        res = dict(zip(menu_items, item_quantity))
        for key in list(res):
            if res[key] == 0:
                del res[key]

        orderSubtotal = 0
        itemDetails = []
        #for each menu_item_id, created an object and collect information on that item: id, name, quantity, price, subtotal
        for key in res:
            response = menuTable.get_item(
                Key={'menu_item_id': key}
            )

            itemDetails.append({
            'item_id': key,
            'item_name': response['Item']['item_name'],
            'quantity': res[key], 
            'item_subtotal': float(response['Item']['item_unit_price']) * res[key],
            'item_unit_price': response['Item']['item_unit_price']
            })
            
            #keep running total of subtotal for the whole order
            orderSubtotal = float(orderSubtotal + float(response['Item']['item_unit_price']) * float(res[key]))
        
        #get name of restaurant for order
        response = restTable.get_item(
            Key={'restaurant_id': restaurant_id}
            )
        restName = response['Item']['restaurant_name']

        #create dict with customer username, order subtotal, and restaurant name to send to front end
        orderDetails = dict(username = customer_username, orderSubtotal = orderSubtotal, restName = restName)
        return render_template('order_summary.html', customer_username=customer_username, customer_id=customer_id, restaurant_id=restaurant_id, order=orderDetails, itemDetails=itemDetails)


#route to complete an order and submit it to the restaurant for processing
@bp.route('/<restaurant_id>/customer/', methods=['GET','POST'])
@check_user_login
def place_order(customer_username, customer_id, restaurant_id):

    if request.method == "POST":
        
        #if customer not logged in, can't place order
        if not customer_id:
            
            flash("You must be logged in to place an order", "danger")
            return redirect(url_for('index'))

        #get various tables needed
        oiTable = dynamodb.Table('order_item') # pylint: disable=no-member
        menuTable = dynamodb.Table('menu_item') # pylint: disable=no-member
        orderTable = dynamodb.Table('order') # pylint: disable=no-member
        restTable = dynamodb.Table('restaurant') # pylint: disable=no-member
        custTable = dynamodb.Table('customer') # pylint: disable=no-member



        
        # generate order_id
        order_id = str(uuid.uuid4())
        
        #get order details from front end
        menu_items = list(request.form.getlist("menu_item_id"))
        quantites = request.form.getlist('item_quantity')
        subtotals = request.form.getlist("item_subtotal")

        #create dict to hold info on order details for each menu item
        sub_order = {}
        for i in range(len(menu_items)):
            
            sub_order[menu_items[i]] = {'Quantity': int(quantites[i]), "subtotal": float(subtotals[i])}
            

        orderSubtotal = 0
        orderIdList = []

        #check to make sure enough menu items exist for order
        for key in sub_order:
            response = menuTable.get_item(
                Key={'menu_item_id': key}
            )

            #if not enough items for order, displays error message
            quantAvailable = int(response['Item']['item_quantity_available'])
            quantRemaining = quantAvailable - sub_order[key]['Quantity']
            if quantRemaining < 0:
                unavailableItem = "We are so sorry, the " + response['Item']['item_name'] + " is unavailable!"
                flash(unavailableItem, "danger")
                redirectUrl = 'restaurant.get_restaurant'
                return redirect(url_for(redirectUrl, restaurant_id = restaurant_id))

        #create an order item for each menu item, linking to order
        for key in sub_order:
            orderItemId = str(uuid.uuid4())
            
            
            item = {
                    'order_id': order_id,
                    'order_item_id': orderItemId,
                    'oi_quantity': sub_order[key]['Quantity'],
                    'oi_unit_price': str(sub_order[key]['subtotal']),
                    'item_id': key
            }


            response = menuTable.get_item(
                Key={'menu_item_id': key}
            )
            quantAvailable = response['Item']['item_quantity_available']
            

            quantRemaining = str(int(quantAvailable) - int(item['oi_quantity']))

            #update quantites of items ordered in database, subtracting items from database that were ordered
            response = menuTable.update_item(
                Key={'menu_item_id': key},
                UpdateExpression='set item_quantity_available = :val',
                ExpressionAttributeValues = {
                    ':val': quantRemaining
                },
                ReturnValues = 'UPDATED_NEW'
            )
            
            #create new order_item with menu item and price
            newOrderItem = oiTable.put_item(
                Item=item
            )
            
            #keep track of order subtotal
            orderSubtotal = orderSubtotal + sub_order[key]['subtotal']
            orderIdList.append(orderItemId)
        

        #get the current time and convert it into a string
        named_tuple = time.localtime() # get struct_time
        time_string = time.strftime("%Y-%m-%d, %H:%M:%S", named_tuple)

        #create confirmation number for order
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
        
        #if somehow user has no email listed, sends error message
        if 'customer_email' not in response['Item']:
            flash('Your profile has no email address.  Please update your information and try again', 'danger')
            return redirect(url_for('index'))

        #get customer email address
        custEmail = response['Item']['customer_email']

        #calculate sales tax for restaurant using zip-tax.com api
        tax_url = 'https://api.zip-tax.com/request/v40?key=' + tax_api_key + '&postalcode=' + str(restZip)

        tax_request = requests.get(tax_url)
        tax_request_content = json.loads(tax_request.content)
        
        salesTax = tax_request_content['results'][0]['taxSales']
        

        #calculate tax for the order
        orderTax = round((salesTax * orderSubtotal), 2)

        #calculate order total (subtotal + order tax)
        orderTotal = str(round(orderTax + orderSubtotal, 2))

        #create order object to be stored in database
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
        order['subtotal'] = str(orderSubtotal)
        order['tax'] = str(orderTax)
        order['order_total'] = orderTotal

        #place order object in database
        createOrder = orderTable.put_item(Item = order)

        #create dict with order details to send back to front end to display to user
        orderDetails = dict(
            username = customer_username, 
            restName = restName, 
            order_time = order['order_time'],
            subtotal = orderSubtotal,
            tax =  orderTax,
            total=orderTotal, 
            confirmation=order['confirmation'],
            restPhone=restPhone)

        #create a confirmation url for user to check status of their order
        confirmation_url = request.url_root + 'order/?confirmation=' + confirmation
        
        #using flask_mail, send email to user with order details and a link they can check to see the status of their order
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
                return redirect(url_for('index')) #render_template('login.html')

        orderTable = dynamodb.Table('order') # pylint: disable=no-member
        restTable = dynamodb.Table('restaurant') # pylint: disable=no-member
        
        row = orderTable.scan(
            FilterExpression=Attr('confirmation').eq(confirmation)
        )
        if row['Count'] == 0:
            flash("The confirmation provided does not exist", "danger")
            return redirect(url_for('index'))
            
        if row['Items'][0]['customer_id'] != customer_id:
            flash('Sorry, you are not the owner of that order.  Permission Denied', 'danger')
            return redirect(url_for('index')) 

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
        
        return render_template('order_status.html', customer_username=customer_username, customer_id=customer_id, order=orderDetails)
<<<<<<< HEAD



    

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







=======
>>>>>>> 40e6f5938dcc81f5c5f098a7cc9cad8a4b10d588
