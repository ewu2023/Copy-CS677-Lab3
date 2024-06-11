from flask import Flask
from flask import request as FlaskRequest
import requests
import json
from threading import Lock

from dotenv import load_dotenv
import os
import sys

# Load in environment variables from .env file
load_dotenv()

# Option for caching
# 0 = cache not in use (do not send invalidation requests)
# 1 = cache in use (send invalidation requests)
USE_CACHE = int(sys.argv[1])

# Initialize catalog host and port from environment variables
CATALOG_HOST = '0.0.0.0'
CATALOG_PORT = int(os.getenv('CATALOG_PORT'))

# Initialize front end host and port from environment variables
FRONT_HOST = os.getenv('FRONT_HOST')
FRONT_PORT = int(os.getenv('FRONT_PORT'))
URL_FRONT_INVALIDATE = f"http://{FRONT_HOST}:{FRONT_PORT}/invalidate"

# Initialize database lock
DB_LOCK = Lock()

""" FLASK APP """
# Initialize in-memory database
memoryDB = {}
with open('catalog_database.json', 'r') as infile:
    memoryDB = json.load(infile)

# Initialize flask app
app = Flask(__name__)

""" Routes """
# GET /lookup/<stock_name> route
# Reply with information about the stock, or reply with an error if it is not in the database
@app.get('/lookup/<stockName>')
def lookup(stockName):
    """ Begin Critical Region """
    DB_LOCK.acquire()

    resJSON = {}
    successFlag = False
    if stockName in memoryDB:
        resJSON = memoryDB[stockName]
        successFlag = True
    else:
        resJSON = {
            "error": {
                "code": 404,
                "message": "stock not found"
            }
        }
    
    DB_LOCK.release()
    """ End Critical Region """

    # Return the appropriate message, depending on if stock was in catalog
    if successFlag:
        # If the stock was in the catalog, return stock info
        return resJSON
    else:
        # If the stock was not in the catalog, return a 404 error message
        return resJSON, 404
    

# POST /update route
# Attempt to update the given stock, or reply with an error if the stock can not be updated
@app.post('/update')
def update():
    """ Begin Critical Region """
    # Lock the database
    DB_LOCK.acquire()

    # Parse the JSON from the request
    requestJSON = FlaskRequest.get_json()
    stockName = requestJSON["name"]
    quantity = requestJSON["quantity"]
    transactionType = requestJSON["type"]

    # Create error message
    errorMsg = {
        "error": {
            "code": 500,
            "message": "failed to update stock"
        }
    }

    # Create success message
    successMsg = {
        "success": {
            "code": 200,
            "message": "updated stock successfully"
        }
    }

    successFlag = False # Set this flag if the update is a success

    if stockName in memoryDB: # Case where a valid stock is being updated
        if transactionType == 'sell':
            # If stock is being sold, increment the number of shares and mark success flag as True
            memoryDB[stockName]["quantity"] += quantity

            # Update on-disk database
            with open('catalog_database.json', 'w') as outfile:
                outfile.write(json.dumps(memoryDB, indent=4))
            successFlag = True
        elif transactionType == 'buy':
            # If the stock is being bought, decrement the number of shares and mark success flag as True
            memoryDB[stockName]["quantity"] -= quantity

            # Update on-disk database
            with open('catalog_database.json', 'w') as outfile:
                outfile.write(json.dumps(memoryDB, indent=4))
            successFlag = True
        else: 
            # Invalid transaction, mark success flag as False
            successFlag = False
    else:
        # Stock was not in the database, so mark success flag as False
        successFlag = False
    
    # Release lock on database
    DB_LOCK.release()
    """ End Critical Region """

    # Send success or error, depending on if the update succeeded
    if successFlag: # Case where update succeeded
        # Check if caching is being used
        if USE_CACHE:
            # Notify front end service that the current stock should be removed
            url = f"{URL_FRONT_INVALIDATE}/{stockName}"
            
            try:
                # For testing: Do not need to start front end service if only testing catalog service
                res = requests.post(url)
            except:
                pass

        # Return success message
        return successMsg
    else:
        # Update failed, so return error
        return errorMsg
    
""" END FLASK APP """    

if __name__ == "__main__":
    app.run(host=CATALOG_HOST, port=CATALOG_PORT)