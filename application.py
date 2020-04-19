import boto3
from boto3.dynamodb.conditions import Key, Attr
from flask import Flask, render_template
import json
import restuarant
import decimal
from decimal import Decimal


application = Flask(__name__)
application.register_blueprint(restuarant.bp)

TABLE_NAME = "customer"
dynamodb_client = boto3.client('dynamodb', region_name="us-west-2")
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('customer') # pylint: disable=no-member


@application.route("/")
def startPage():
	print(dynamodb)
	response = dynamodb_client.query(
		TableName='customer',
		KeyConditionExpression='customer_id = :customer_id',
		ExpressionAttributeValues = {
			':customer_id': {'S': '0e37d916-f960-4772-a25a-01b762b5c1bd'}
		}
	)
	#itemList = json.dumps(response['Items'][0])
	# print(json.dumps(response['Items']))
	
	return (json.dumps(response['Items']))


@application.route("/login")
def loginPage():
	return render_template('login.html')

@application.route("/menu")
def menuPage():
	table=dynamodb.Table('menu_item')
	response = table.scan(
		FilterExpression=Attr('menu_id').eq('menu_1')
	)
	data = json.dumps(response['Items'], cls=DecimalEncoder)
	for i in range(len(data)):
		print(data[i])

	print(len(data))

	return render_template('menu.html', response=data)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

if __name__ == '__main__':
    application.run(host='127.0.0.1', port=8080, debug=True)