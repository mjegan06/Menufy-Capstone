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
import random
import string
import decimal
import uuid
from flask_mail import Mail, Message

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('restaurant') # pylint: disable=no-member

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

bp = Blueprint('business', __name__, url_prefix='/business')

# Display the business dashboard
@bp.route('/<rid>/home', methods=['GET', 'POST'])
@business_check_user_login
def business_home(restaurant_username, restaurant_id, rid):

    # edit restaurant details            
    if request.method == 'POST': 
        try:
            #get the data from the table
            data = request.form.to_dict(flat=False)
            keyList = list(data.keys())
            key = keyList[0]
            
            #if missing the restaurant_id throw an error
            input = data[key][0]
            if input == '':
                return ("",400)
            
            #update the dynamodb restaurant table with updated info
            table = dynamodb.Table('restaurant')
            response = table.get_item(Key={'restaurant_id': restaurant_id})
            item = response['Item']
            item[key] = input
            table.put_item(Item=item)
            

        except:
            print("error")
            
    table = dynamodb.Table('restaurant') # pylint: disable=no-member
    
    # get restaurant details to display
    restaurant= table.query(
        KeyConditionExpression=Key('restaurant_id').eq(restaurant_id)
    )
    restaurant_name = restaurant['Items'][0]['restaurant_name']

    data = json.dumps(restaurant['Items'], cls=DecimalEncoder).replace(r"'",r"\'")

    return render_template('business_home.html', restaurant_name = restaurant_name, restaurant_username=restaurant_username, restaurant_id=restaurant_id, data=data)

# display the orders for the restaurant
@bp.route('/<rid>/orders', methods=['GET', 'POST'])
@business_check_user_login
def business_orders(restaurant_username, restaurant_id, rid):
    
    # update the order status
    if request.method == 'POST':  
        try:
            order_id =  request.form['change-status']
            table = dynamodb.Table('order')
            response = table.get_item(Key={'order_id': order_id})
            item = response['Item']
            
            if ( item['order_status']=='Completed'):
                item['order_status']='In-progress'
                table.put_item(Item=item)               
            
            elif ( item['order_status']=='In-progress'):
                item['order_status']='Completed'
                table.put_item(Item=item)

            elif ( item['order_status']=='Submitted'):
                item['order_status']='In-progress'
                table.put_item(Item=item)

        except:

            print("Phew")
        
    
    restaurant_table=dynamodb.Table('restaurant')
    order_table=dynamodb.Table('order')

    #get restaurant name
    restaurant_data = restaurant_table.query(
        KeyConditionExpression=Key('restaurant_id').eq(restaurant_id)
    )
    restaurant_name = restaurant_data['Items'][0]['restaurant_name']

    #scan the orders for all the orders for that restaurant
    orders = order_table.scan( FilterExpression=Key('restaurant_id').eq(restaurant_id))

    order_data = json.dumps(orders['Items'], cls=DecimalEncoder)

    return render_template('business_orders.html', restaurant_username=restaurant_username, restaurant_id=restaurant_id, restaurant_name = restaurant_name, order_data = order_data)

# get order details (modal)   
@bp.route('/<rid>/<order_id>', methods=['GET'])
@business_check_user_login
def get_order_details(restaurant_username, restaurant_id, rid, order_id):

    order_table=dynamodb.Table('order')

    #get the order details for that order_id
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

# business inventory display
@bp.route('/<rid>/inventory', methods=['GET'])
@business_check_user_login
def business_inventory(restaurant_username, restaurant_id, rid):

    # get restaurant name
    table = dynamodb.Table('restaurant') # pylint: disable=no-member
    row = table.scan(
        FilterExpression=Attr('restaurant_id').eq(restaurant_id)
    )
    restaurant_name = row['Items'][0]['restaurant_name']

    # get menu id
    menu_table=dynamodb.Table('menu') # pylint: disable=no-member
    response = menu_table.scan(
        FilterExpression=Attr('restaurant_id').eq(restaurant_id)
    )
    
    #if there is no menu for the restaurant
    if not response['Items']:
        menu_data = None
        flash("Unable to find a menu associated with your business, please create a menu to access this feature", "danger")
        return render_template('business_inventory.html', restaurant_name = restaurant_name, restaurant_username=restaurant_username, restaurant_id=restaurant_id, menu_data=menu_data)

    # get menu item details from the menu item table
    else:
        menu_id = response['Items'][0]['menu_id']

        # get menu items
        menu_item_table=dynamodb.Table('menu_item') # pylint: disable=no-member
        response = menu_item_table.scan(
            FilterExpression=Attr('menu_id').eq(menu_id)
        )
        
        menu_data = json.dumps(response['Items'], cls=DecimalEncoder)

        return render_template('business_inventory.html', restaurant_name = restaurant_name, restaurant_username=restaurant_username, restaurant_id=restaurant_id, menu_data=menu_data)

# get business menu
@bp.route('/<rid>/menu', methods=['GET'])
@business_check_user_login
def business_menu(restaurant_username, restaurant_id, rid):

    #get restaurant name        
    table = dynamodb.Table('restaurant') # pylint: disable=no-member
    row = table.scan(
        FilterExpression=Attr('restaurant_id').eq(restaurant_id)
    )
    restaurant_name = row['Items'][0]['restaurant_name']

    # get menu id
    menu_table=dynamodb.Table('menu') # pylint: disable=no-member
    response = menu_table.scan(
        FilterExpression=Attr('restaurant_id').eq(restaurant_id)
    )
    
    # if menu doesn't exist throw an error
    if not response['Items']:
        menu_data = None
        flash("Unable to find a menu associated with your business, please create a menu to access this feature", "danger")
        return render_template('business_inventory.html', restaurant_name = restaurant_name, restaurant_username=restaurant_username, restaurant_id=restaurant_id, menu_data=menu_data)

    # get the menu items for the menu
    else:
        menu_id = response['Items'][0]['menu_id']

        # get menu items
        menu_item_table=dynamodb.Table('menu_item') # pylint: disable=no-member
        response = menu_item_table.scan(
            FilterExpression=Attr('menu_id').eq(menu_id)
        )

        menu_data = json.dumps(response['Items'], cls=DecimalEncoder).replace(r"'",r"\'")

        return render_template('business_menu.html', restaurant_name = restaurant_name, restaurant_username=restaurant_username, restaurant_id=restaurant_id, menu_data=menu_data)

# add menu item to the current menu
@bp.route('/<rid>/add_menu_item', methods=['POST'])
@business_check_user_login
def add_menu_item(restaurant_username, restaurant_id, rid):

    #if a request to add a menu item is submitted
    if request.method == 'POST':  
        try:
            # get the form information including item name, item description, item quantity, item type and unit price
            data = request.form.to_dict(flat=False)
            item = {}

            #generate a random menu_item_id
            menu_item_id = "".join([random.choice(string.ascii_uppercase + string.digits) for n in range(8)])

            #if any information is missing or the item_unit_price/item_quantity_available are < 0, throw an error
            keys = list(data.keys())
            for each in keys:
                if data[each][0] == '':
                    return ("",400)
                if each == 'item_unit_price' or each == 'item_quantity_available':
                    if(float(data[each][0]) < 0):
                        return ("",400)                
                item[each] = data[each][0]

            #set the menu_item_id
            item['menu_item_id'] = menu_item_id

            # get the menu_id for the restaurant and add the menu_item to menu_item table.
            table=dynamodb.Table('menu_item') # pylint: disable=no-member
            menu_table=dynamodb.Table('menu') # pylint: disable=no-member
            response = menu_table.scan(
                FilterExpression=Attr('restaurant_id').eq(restaurant_id)
            )
            menu_id = response['Items'][0]['menu_id']
            item['menu_id']=menu_id
            table.put_item(Item=item)

        except:
            return ("")

    return ("")

# edit menu item
@bp.route('/<menu_item_id>', methods=['GET', 'POST'])
@business_check_user_login
def edit_menu_item(restaurant_username, restaurant_id, menu_item_id):

    # display modal with menu_item information populating the form
    if request.method == 'GET':  
        try:
           # get menu items
            menu_item_table=dynamodb.Table('menu_item') # pylint: disable=no-member
            response = menu_item_table.scan(
                FilterExpression=Attr('menu_item_id').eq(menu_item_id)
            )
            return (json.dumps(response["Items"][0], cls=DecimalEncoder))
        except:
            return ("")

    # update the menu item information
    elif request.method == 'POST':
        try:
            # get the data from the form submission
            data = request.form.to_dict(flat=False)

           # get menu items
            menu_item_table=dynamodb.Table('menu_item') # pylint: disable=no-member
            response = menu_item_table.scan(
                FilterExpression=Attr('menu_item_id').eq(menu_item_id)
            )
            item = response["Items"][0]

            #if any information is missing or the item_unit_price/item_quantity_available are < 0, throw an error
            keys = list(data.keys())
            for each in keys:
                if data[each][0] == '':
                    return ("",400)
                if each == 'item_unit_price' or each == 'item_quantity_available':
                    if(float(data[each][0]) < 0):
                        return ("",400) 
                item[each] = data[each][0]

            #update the menu_item
            menu_item_table.put_item(Item=item)
    
        except:
            return ("")

    return ("")

# delete a menu_item from restaurants menu
@bp.route('/delete/<menu_item_id>', methods=['POST'])
@business_check_user_login
def delete_menu_item(restaurant_username, restaurant_id, menu_item_id):
    if request.method == 'POST':
        try:
            # get menu items
            menu_item_table=dynamodb.Table('menu_item') # pylint: disable=no-member
            response = menu_item_table.scan(
                FilterExpression=Attr('menu_item_id').eq(menu_item_id)
            )
            item = response["Items"][0]
            key = item['menu_item_id']
            # delete menu_item
            menu_item_table.delete_item(Key={
            'menu_item_id': key
        })
        except:
            return ("")  
    return ("")

# reorder menu item
@bp.route('/reorder/<menu_item_id>', methods=['POST'])
@business_check_user_login
def reorder_item(restaurant_username, restaurant_id, menu_item_id):
            
    if request.method == 'POST':
        try:
            #use email information from application.py
            from application import mail as mail

            #get the item info from menu_item table
            menu_item_table=dynamodb.Table('menu_item') # pylint: disable=no-member
            response = menu_item_table.scan(
                FilterExpression=Attr('menu_item_id').eq(menu_item_id)
            )
            menu_item = response["Items"][0]

            #get the restaurant info from the restaurant table table
            table = dynamodb.Table('restaurant')
            response= table.get_item(Key={'restaurant_id': restaurant_id})
            restaurant = response["Item"]

            #create a message to send to the restaurant. Normally we would have created another column in the menu_item table that was for an email address of the supplier but,
            # we didn't want the TA or Instructor to have to create a new email just for that section so we are going to use the restaurant email as the same email address of the fake supplier.
            msg = Message(str(restaurant['restaurant_name']) + ": Restock Inventory Request",
                sender = "menufy.capstone@gmail.com",
                recipients= [restaurant['restaurant_email']])
            msg.body = 'Hello Procurement Team, \n\n Please fulfill the following order for ' + str(restaurant['restaurant_name']) + '\n\n' + 'We are running low on ' + str(menu_item['item_name']) +' and would like to replenish our stock with the default stock order in our contract. \n\n' +'Please call us if you have any issues fulfilling this order at ' + str(restaurant['restaurant_phone_num']) + '.\n\n\n' + 'Sincerely, \n ' + str(restaurant['restaurant_name']) + '\n' + str(restaurant['restaurant_address_line1']) + '\n' + str(restaurant['restaurant_address_line2']) + '\n' + str(restaurant['restaurant_city']) + '\n' + str(restaurant['restaurant_postal_code']) + '\n' + str(restaurant['restaurant_state'])
            #send email and display a success message on the screen
            mail.send(msg)
            confirmationMessage = "Order was successful. Confirmation email sent to vendor"
            flash(confirmationMessage, "success")
            return ("")
            
        except Exception as e:
            flash("Order did not go through. Try again.", "warning")
            return str(e)
    