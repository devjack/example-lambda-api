#!/usr/bin/env python
import os
import json
import logging
import boto3
from boto3.dynamodb.conditions import Attr, Key
from flask import Flask, jsonify, request
from flask.wrappers import Response
import uuid


app = Flask(__name__)
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

QUOTES_TABLE = os.environ['quotesTable']

dynamodb_client = boto3.resource("dynamodb")
quotesTable = dynamodb_client.Table(QUOTES_TABLE)

@app.route('/', methods=['GET'])
def root(event=None, context=None):
    return jsonify({"message": "OK"})

def seed_data():
    for q in json.load(open('quotes.json')):
        quotesTable.put_item(
            Item={
                'quoteKey': str(uuid.uuid4()),
                'quote': q['quote'],
                'author': q['author'],
            }, 
            ConditionExpression='attribute_not_exists(quoteKey)'
        )

def scan_quotes(key):
    quotes_scan = quotesTable.scan(
        FilterExpression= "attribute_not_exists(#O) OR #O = :o",
        ExpressionAttributeValues={
            ":o": key
        },
        ExpressionAttributeNames={
            "#O": "owner"
        }
    )
    return quotes_scan['Items']

@app.route('/quotes', methods=['GET'])
def index(event=None, context=None):
    
    if not request.headers.has_key("x-api-key"):
        return Response(json.dumps({"message":"API Key is required for retrieving quotes"}), status=400, mimetype='application/json')

    data = scan_quotes(request.headers['x-api-key'])

    if not data:
        seed_data() # A horrible hack to seed an empty database, but its a demo so don't judge!
        data = scan_quotes(request.headers['x-api-key'])

    response = [{'id': q['quoteKey'], 'quote': q['quote'], 'author': q['author']} for q in data]
    return jsonify(response)


@app.route('/quotes', methods=['POST'])
def store():
    logger.error('POST /quotes not yet implemented')
    logger.info(request.headers.has_key('x-api-key'))
    if not request.headers.has_key("x-api-key"):
        return Response(json.dumps({"message":"API Key is required for creating quotes"}), status=400, mimetype='application/json')
    
    content = request.get_json(force=True)

    document = {
        'quoteKey': str(uuid.uuid4()),
        'quote': content['quote'],
        'author': content['author'],
        'owner': request.headers["x-api-key"]
    }

    quotesTable.put_item(
        Item=document, 
        ConditionExpression='attribute_not_exists(quoteKey)'
    )

    return jsonify(document)

if __name__ == '__main__':
    app.run(debug=True)