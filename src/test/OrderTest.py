import requests
import os
from dotenv import load_dotenv

# Initialize order service host and port
# Assumes order service with ID 1 is running
# After starting the order service, make sure to start the catalog and front end services
load_dotenv()
ORDER_HOST = os.getenv('ORDER_1_HOST')
ORDER_PORT = os.getenv('ORDER_1_PORT')

# Initialize base URL to use for requests
URL_ORDER_BASE = f"http://{ORDER_HOST}:{ORDER_PORT}"
URL_BUY = f"{URL_ORDER_BASE}/buy"
URL_SELL = f"{URL_ORDER_BASE}/sell"

# Initialize stocks to test
VALID_STOCK_OPTION = "GameStart"
INVALID_STOCK_OPTION = "Pear"

# Test if buying a valid stock returns correct result
def test_valid_buy():
    # Initialize JSON to send to buy endpoint
    bodyJSON = {
        "name": VALID_STOCK_OPTION,
        "quantity": 10
    }

    # Send request to endpoint and parse JSON
    res = requests.post(URL_BUY, json=bodyJSON)
    resJSON = res.json()

    # Print result
    try:
        assert("error" not in resJSON)
        assert("transaction-number" in resJSON)
        print("Passed test_valid_buy")
        print(f"Received Message from Order Service: {resJSON}\n")
        
        # Return True that this test succeeded, as well as the name of the test
        return (True, 'test_valid_buy') 
    except:
        print("Failed test_valid_buy")
        print(f"Received Message from Order Service: {resJSON}\n")

        # Return False to denote this test failed, as well as the name of the test
        return (False, 'test_valid_buy') 

# Test if selling a valid stock returns correct result
def test_valid_sell():
    # Initialize JSON to send to buy endpoint
    bodyJSON = {
        "name": VALID_STOCK_OPTION,
        "quantity": 10
    }

    # Send request to endpoint and parse JSON
    res = requests.post(URL_SELL, json=bodyJSON)
    resJSON = res.json()

    # Print result
    try:
        assert("error" not in resJSON)
        assert("transaction-number" in resJSON)
        print("Passed test_valid_sell")
        print(f"Received Message from Order Service: {resJSON}\n")

        return (True, 'test_valid_sell')
    except:
        print("Failed test_valid_sell")
        print(f"Received Message from Order Service: {resJSON}\n")

        return (False, 'test_valid_sell')

# Test if buying an invalid stock returns right error
def test_invalid_buy():
    # Initialize JSON to send to buy endpoint
    bodyJSON = {
        "name": INVALID_STOCK_OPTION,
        "quantity": 10
    }

    # Send request to endpoint and parse JSON
    res = requests.post(URL_BUY, json=bodyJSON)
    resJSON = res.json()

    # Print result
    try:
        assert("error" in resJSON)
        
        # Get the top level error object
        errorObj = resJSON["error"]
        code = errorObj["code"]

        # Assert that the correct code was returned
        assert(code == 404)

        print("Passed test_invalid_buy")
        print(f"Received Message from Order Service: {resJSON}\n")

        return (True, 'test_invalid_buy')
    except:
        print("Failed test_invalid_buy")
        print("Expected error code: 404")
        print(f"Received Message from Order Service: {resJSON}\n")

        return (False, 'test_invalid_buy')

# Test if selling an invalid stock returns right error
def test_invalid_sell():
    # Initialize JSON to send to buy endpoint
    bodyJSON = {
        "name": INVALID_STOCK_OPTION,
        "quantity": 10
    }

    # Send request to endpoint and parse JSON
    res = requests.post(URL_SELL, json=bodyJSON)
    resJSON = res.json()

    # Print result
    try:
        assert("error" in resJSON)
        
        # Get the top level error object
        errorObj = resJSON["error"]
        code = errorObj["code"]

        # Assert that the correct code was returned: in this case a 404
        assert(code == 404)

        print("Passed test_invalid_sell")
        print(f"Received Message from Order Service: {resJSON}\n")

        return (True, 'test_invalid_sell')
    except:
        print("Failed test_invalid_sell")
        print("Expected error code: 404")
        print(f"Received Message from Order Service: {resJSON}\n")

        return (False, 'test_invalid_sell')

# Test if requesting to buy more than the number of shares available returns error
def test_buy_over_limit():
    # Initialize JSON to send to buy endpoint
    bodyJSON = {
        "name": VALID_STOCK_OPTION,
        "quantity": 200
    }

    # Send request to endpoint and parse JSON
    res = requests.post(URL_BUY, json=bodyJSON)
    resJSON = res.json()

    # Print result
    try:
        assert("error" in resJSON)
        
        # Get the top level error object
        errorObj = resJSON["error"]
        code = errorObj["code"]

        # Assert that the correct code was returned
        assert(code == 500)

        print("Passed test_buy_over_limit")
        print(f"Received Message from Order Service: {resJSON}\n")

        return (True, 'test_buy_over_limit')
    except:
        print("Failed test_buy_over_limit")
        print("Expected error code: 500")
        print(f"Received Message from Order Service: {resJSON}\n")

        return (False, 'test_buy_over_limit')
    
# Test if successive transaction IDs are unique and increment from the previous one
def test_successive_transaction_ids():
    # Initialize JSON to send to buy and sell endpoints
    buyJSON = {
        "name": VALID_STOCK_OPTION,
        "quantity": 10
    }

    sellJSON = {
        "name": VALID_STOCK_OPTION,
        "quantity": 10
    }

    buyRes = (requests.post(URL_BUY, json=buyJSON)).json()
    sellRes = (requests.post(URL_SELL, json=sellJSON)).json()

    # Print results
    try:
        assert("error" not in buyRes and "error" not in sellRes) # Check that neither returned an error

        # Get transaction IDs for both requests
        buyTransactionID = buyRes["transaction-number"]
        sellTransactionID = sellRes["transaction-number"]

        # Test for equality and uniqueness
        assert(buyTransactionID != sellTransactionID)

        # Since the buy occurred before the sell, sell's ID should be higher
        assert(sellTransactionID > buyTransactionID)
        assert(sellTransactionID == buyTransactionID + 1)

        print("Passed test_successive_transaction_ids")
        print(f"Received Buy Message from Order Service: {buyRes}")
        print(f"Received Sell Message from Order Service: {sellRes}")

        return (True, 'test_successive_transaction_ids')
    except:
        print("Failed test_successive_transaction_ids")
        print(f"Received Buy Message from Order Service: {buyRes}")
        print(f"Received Sell Message from Order Service: {sellRes}")

        return (False, 'test_successive_transaction_ids')
        

# Run each test
if __name__ == "__main__":
    # List of tests
    # Tests will be run in the order they appear
    tests = [
        test_valid_buy,
        test_valid_sell,
        test_invalid_buy,
        test_invalid_sell,
        test_buy_over_limit,
        test_successive_transaction_ids
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