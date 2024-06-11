import requests
import os
from dotenv import load_dotenv

# Load in environment variables
load_dotenv()

# Set global vars
CATALOG_HOST = os.getenv('CATALOG_HOST') # Get catalog host
CATALOG_PORT = int(os.getenv('CATALOG_PORT')) # Get catalog host's port

# Set URLs
URL_BASE = f"http://{CATALOG_HOST}:{CATALOG_PORT}"
URL_LOOKUP = f"{URL_BASE}/lookup"
URL_UPDATE = f"{URL_BASE}/update"

# Set names of stocks to look up
VALID_STOCK_OPTION = "GameStart"
INVALID_STOCK_OPTION = "Pear"

# Test looking up a valid stock
def test_lookup_valid_stock():
    # Send lookup request
    url = f"{URL_LOOKUP}/{VALID_STOCK_OPTION}"
    lookupRes = requests.get(url)
    resJSON = lookupRes.json()

    # Print results
    try:
        # Assert that no error was returned
        assert("error" not in resJSON)

        # Assert that correct stock was returned
        assert(resJSON["name"] == VALID_STOCK_OPTION)

        print("Passed test_lookup_valid_stock")
        print(f"Message received from Catalog: {resJSON}\n")
        return (True, 'test_lookup_valid_stock')
    except:
        print("Failed test_lookup_valid_stock")
        print(f"Message received from Catalog: {resJSON}\n")
        return (False, 'test_lookup_valid_stock')

# Test looking up an invalid stock returns an error
def test_lookup_invalid_stock():
    # Send lookup request
    url = f"{URL_LOOKUP}/{INVALID_STOCK_OPTION}"
    lookupRes = requests.get(url)
    resJSON = lookupRes.json()

    try:
        # Assert that an error was returned
        assert("error" in resJSON)
        
        # Assert that the correct error code was returned
        errorObj = resJSON["error"]
        code = errorObj["code"]
        assert(code == 404)

        print("Passed test_lookup_invalid_stock")
        print(f"Message received from Catalog: {resJSON}\n")
        return (True, "test_lookup_invalid_stock")
    except:
        print("Failed test_lookup_invalid_stock")
        print(f"Message received from Catalog: {resJSON}\n")
        return (False, "test+lookup_invalid_stock")

# Test incrementing a valid stock
def test_increment_valid_stock():
    # Format URL to send lookup request to
    lookupUrl = f"{URL_LOOKUP}/{VALID_STOCK_OPTION}"

    # Format JSON to send with update request
    updateRequestJSON = {
        "name": VALID_STOCK_OPTION,
        "quantity": 10,
        "type": "sell"
    }

    # Send a lookup request first. This will be used to compare the results after the update.
    lookupRes1 = requests.get(lookupUrl)

    # Send update request to increment shares of the valid stock option
    updateRes = requests.post(URL_UPDATE, json=updateRequestJSON)

    # Send a lookup request after the update
    lookupRes2 = requests.get(lookupUrl)

    try:
        # Get JSON from both lookup and update responses
        lookupJSON_1 = lookupRes1.json()
        lookupJSON_2 = lookupRes2.json()
        updateJSON = updateRes.json()

        # Assert that no request returned an error
        assert("error" not in lookupJSON_1)
        assert("error" not in lookupJSON_2)
        assert("error" not in updateJSON)

        # Assert that the update returned a success object
        assert("success" in updateJSON)

        # Assert that the quantity of the stock was incremented
        quantityBefore = lookupJSON_1["quantity"]
        quantityAfter = lookupJSON_2["quantity"]

        assert(quantityAfter > quantityBefore)
        assert(quantityAfter == (quantityBefore + 10))

        print("Passed test_increment_valid_stock")
        print(f"Lookup before increment: {lookupJSON_1}")
        print(f"Lookup after increment: {lookupJSON_2}\n")
        return (True, 'test_increment_valid_stock')
    except:
        print("Failed test_increment_valid_stock")
        print(f"Message from Catalog: {updateRes.json()}\n")
        return (False, 'test_increment_valid_stock')

# Test decrementing a valid stock
def test_decrement_valid_stock():
    # Format URL to send lookup request to
    lookupUrl = f"{URL_LOOKUP}/{VALID_STOCK_OPTION}"

    # Format JSON to send with update request
    updateRequestJSON = {
        "name": VALID_STOCK_OPTION,
        "quantity": 10,
        "type": "buy"
    }

    # Send a lookup request first. This will be used to compare the results after the update.
    lookupRes1 = requests.get(lookupUrl)

    # Send update request to increment shares of the valid stock option
    updateRes = requests.post(URL_UPDATE, json=updateRequestJSON)

    # Send a lookup request after the update
    lookupRes2 = requests.get(lookupUrl)

    try:
        # Get JSON from both lookup and update responses
        lookupJSON_1 = lookupRes1.json()
        lookupJSON_2 = lookupRes2.json()
        updateJSON = updateRes.json()

        # Assert that no request returned an error
        assert("error" not in lookupJSON_1)
        assert("error" not in lookupJSON_2)
        assert("error" not in updateJSON)

        # Assert that the update returned a success object
        assert("success" in updateJSON)

        # Assert that the quantity of the stock was incremented
        quantityBefore = lookupJSON_1["quantity"]
        quantityAfter = lookupJSON_2["quantity"]

        assert(quantityAfter < quantityBefore)
        assert(quantityAfter == (quantityBefore - 10))

        print("Passed test_decrement_valid_stock")
        print(f"Lookup before decrement: {lookupJSON_1}")
        print(f"Lookup after decrement: {lookupJSON_2}\n")
        return (True, 'test_decrement_valid_stock')
    except:
        print("Failed test_decrement_valid_stock")
        print(f"Message from Catalog: {updateRes.json()}\n")
        return (False, 'test_decrement_valid_stock')

# Test updating an invalid stock returns an error message
def test_update_invalid():
    # Format body json for buy and sell requests
    buyJSON = {
        "name": INVALID_STOCK_OPTION,
        "quantity": 10,
        "type": "buy"
    }

    sellJSON = {
        "name": INVALID_STOCK_OPTION,
        "quantity": 10,
        "type": "sell"
    }

    # Send both buy and sell requests for the invalid stock
    buyRes = requests.post(URL_UPDATE, json=buyJSON)
    sellRes = requests.post(URL_UPDATE, json=sellJSON)

    buyJSON = buyRes.json()
    sellJSON = sellRes.json()

    try:
        # Assert that an error was returned for both requests
        assert("error" in buyJSON)
        assert("error" in sellJSON)

        # Assert that the correct error codes were returned; in this case it should be 500
        buyErr = buyJSON["error"]
        sellErr = buyJSON["error"]

        assert(buyErr["code"] == 500)
        assert(sellErr["code"] == 500)

        print("Passed test_update_invalid")
        print(f"Message received when attempting to increment: {buyJSON}")
        print(f"Message received when attempting to decrement: {sellJSON}\n")
        return (True, 'test_update_invalid')
    except:
        print("Failed test_update_invalid")
        print(f"Message received when attempting to increment: {buyJSON}")
        print(f"Message received when attempting to decrement: {sellJSON}\n")
        return (False, 'test_update_invalid')




if __name__ == "__main__":
    # List of tests
    # Tests will be run in the order they appear
    tests = [
        test_lookup_valid_stock,
        test_lookup_invalid_stock,
        test_increment_valid_stock,
        test_decrement_valid_stock,
        test_update_invalid
    ]

    # Run each test
    numPassed = 0
    numFailed = 0
    failedTests = []
    for test in tests:
        passed, testName = test()
        if passed:
            numPassed += 1
        else:
            numFailed += 1
            failedTests.append(testName)
    
    # Print each test failed
    print('--------------------')
    if numFailed > 0:
        for failedTest in failedTests:
            print(failedTest)
    else:
        print("All passed!")
