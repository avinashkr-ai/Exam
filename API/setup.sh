#!/bin/bash
# This script is used to set up a virtual environment and run the Flask server
python3 -m venv venv

# activate the virtual environment
source venv/bin/activate

# install requirements
pip install -r requirements.txt

# db init
flask db init
flask db migrate
flask db upgrade
