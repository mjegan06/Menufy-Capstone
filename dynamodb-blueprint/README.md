# To create table

aws dynamodb create-table --cli-input-json file://~/environment/test/dynamodb-customer.json

# To populate table with sample data
aws dynamodb batch-write-item --request-items file://~/environment/test/populate-customer.json

# to scan table
aws dynamodb scan --table-name customer
