#!/bin/bash
# Use this shell script to reset databases for each microservice

git checkout catalog/catalog_database.json
git checkout orders/order1_database.json
git checkout orders/order2_database.json
git checkout orders/order3_database.json