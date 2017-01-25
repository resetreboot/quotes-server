#!/bin/bash

nginx
cd /quotes-server
python3 deploy.py && python3 quotes.py
