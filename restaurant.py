import boto3
from boto3.dynamodb.conditions import Key
from flask import Blueprint, request, make_response
import json
import decimal

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


@bp.route('/<id>', methods=['GET'])
def get_restaurant(id):
	response = table.get_item(
		Key={'restaurant_id': id}
	)

	return (json.dumps(response['Item'], cls=DecimalEncoder))


