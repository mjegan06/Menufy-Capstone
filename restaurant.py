import boto3
from boto3.dynamodb.conditions import Key
from flask import Blueprint, request, make_response, flash
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

@bp.route('', methods=['GET'])
def get_all_restaurants():
	response = table.scan()
	print("Number of items in restaurant table: ", response['Count'])

	return (json.dumps(response['Items'], cls=DecimalEncoder))

@bp.route('', methods=['POST'])
def create_restaurant():

	content = request.get_json()

	# generate random UUID for restaurant_id
	new_restaurant_id = str(uuid.uuid4())

	response_item = table.put_item(
            Item={
				'restaurant_id': new_restaurant_id,
				'restaurant_name': content['restaurant_name'],
				'restaurant_latitude': content['restaurant_latitude'],
				'restaurant_longitude': content['restaurant_longitude'],
				'phone_num': content['phone_num'],
				'address_line1': content['address_line1'],
				'address_line2': content['address_line2'],
				'city': content['city'],
				'state': content['state'],
				'postal_code': content['postal_code']
			}
        )

	return(new_restaurant_id, 201, {'Content-Type': 'application/json'})



@bp.route('/<rid>', methods=['GET'])
def get_restaurant(rid):
	response = table.get_item(
		Key={'restaurant_id': rid}
	)

	return (json.dumps(response['Item'], cls=DecimalEncoder), 200, {'Content-Type': 'application/json'})

@bp.route('/<rid>', methods=['DELETE'])
def delete_restaurant(rid):
	response = table.delete_item(
		Key={'restaurant_id': rid}
	)

	return ("", 204)


