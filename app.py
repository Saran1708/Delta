from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from fyers_apiv3 import fyersModel
from selenium import webdriver
import os
import pandas as pd
import datetime as dt
import webbrowser
from datetime import datetime


app = Flask(__name__)

client_id = "V93AXT1M3E-100"
secret_key = "1VBSFLDXWS"
redirect_uri = "http://127.0.0.1:5000/callback"
response_type = "code"
state = "sample"
grant_type = "authorization_code"

app.secret_key = 'abcxyz'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1708'
app.config['MYSQL_DB'] = 'db'

mysql = MySQL(app)

# Define fyers globally
fyers = None

def get_fyers_instance():
    with open("access.txt", 'r') as r:
        access_token = r.read()

    client_id = "V93AXT1M3E-100"
    return fyersModel.FyersModel(token=access_token, log_path=os.getcwd(), client_id=client_id)

def fetch_and_process_data(fyers, symbol, range_from, range_to):
    data = {
        "symbol": symbol,
        "resolution": "1",
        "date_format": "1",
        "range_from": range_from,
        "range_to": range_to,
        "cont_flag": "1"
    }

    sdata = fyers.history(data)
    sdata = pd.DataFrame(sdata['candles'])
    sdata.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    sdata['date'] = pd.to_datetime(sdata['date'], unit='s')
    sdata.date = (sdata.date.dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata'))
    sdata['date'] = sdata['date'].dt.tz_localize(None)
    sdata = sdata.set_index('date')

    return sdata

def calculate_price_difference(sdata):
    candle_920 = sdata.between_time('09:20', '09:21').iloc[0]
    candle_930 = sdata.between_time('09:30', '09:31').iloc[0]

    price_difference = candle_920['open'] - candle_930['open']
    absolute_price_difference = abs(price_difference)
    return absolute_price_difference

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s AND password = %s', (email, password,))
        user = cursor.fetchone()
        if user:
            session['loggedin'] = True
            session['name'] = user['name']
            session['email'] = user['email']
            message = 'Logged in successfully!'
            return render_template('index.html', message=message)
        else:
            message = 'Please enter correct email/password!'
    return render_template('login.html', message=message)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form:
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        account = cursor.fetchone()
        if account:
            message = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address!'
        elif not name or not password or not email:
            message = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO user (name, email, password) VALUES (%s, %s, %s)', (name, email, password,))
            mysql.connection.commit()
            message = 'You have successfully registered!'
    elif request.method == 'POST':
        message = 'Please fill out the form!'

    return render_template('register.html', message=message)


@app.route('/stop_loss_calculator')
def stop_loss_calculator():
    return render_template('sl.html')

with open("access.txt", 'r') as r:
    access_token = r.read()
    
client_id = "V93AXT1M3E-100"
fyers = fyersModel.FyersModel(token=access_token, log_path=os.getcwd(), client_id=client_id)

@app.route('/execute', methods=['POST'])
def execute():
    try:
        # Execute Fyers API code
        data = request.json
        transactionType = data['transactionType']
        instrument = data['instrument']
        quantity = data['quantity']

        side = 1 if transactionType == 'buy' else -1
        data = {
            "symbol":instrument,
            "qty": quantity,
            "type": 2,
            "side": side,
            "productType": "INTRADAY",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
            "orderTag": "tag1"
        }
        response = fyers.place_order(data=data)

        # Log response
        print(response)

        return jsonify({"status": "success", "message": "Order executed successfully", "response": response})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/position_sizing_calculator')
def position_sizing_calculator():
    return render_template('ps.html')

@app.route('/delta_calculator', methods=['GET', 'POST'])
def delta_calculator():
    global fyers  # Ensure fyers is accessible globally
    if request.method == 'POST':
        instrument = request.form['instrument']
        contract = request.form['contract']
        expiry = request.form['date']
        strike_price = request.form['strikePrice']
        option_type = request.form['optionType']
        
        # Splitting the expiry date into day, month, and year
        expiry_date = dt.datetime.strptime(expiry, '%Y-%m-%d')
        day = "{:02d}".format(expiry_date.day)  # Ensuring day is two digits
        year = str(expiry_date.year)[-2:]  # Storing only last two digits of the year
        
        # Check if the expiry is weekly or monthly
        if contract == 'weekly':
            weekly_expiry_date = expiry_date
        else:
            monthly_expiry_date = expiry_date
        
        # Mapping month to the specified format
        if contract == 'weekly':
            month_mapping = {
                1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6',
                7: '7', 8: '8', 9: '9', 10: 'O', 11: 'N', 12: 'D'
            }
        else:  # Monthly contract
            month_mapping = {
                1: 'JAN', 2: 'FEB', 3: 'MAR', 4: 'APR', 5: 'MAY', 6: 'JUN',
                7: 'JUL', 8: 'AUG', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DEC'
            }
        
        if contract == 'weekly':
            month = str(weekly_expiry_date.month)  # For weekly expiry, month is represented by the number
        else:
            month = month_mapping[monthly_expiry_date.month]  # Getting the mapped value for the month
        
        if instrument == 'Nifty':
            symbol1 = "NSE:NIFTY50-INDEX"
            sym="NSE:NIFTY"
        elif instrument == 'BankNifty':
            symbol1 = "NSE:NIFTYBANK-INDEX"
            sym="NSE:BANKNIFTY"
        elif instrument == 'Finfity':
            symbol1 = "NSE:FINNIFTY-INDEX"
            sym="NSE:FINNIFTY"
        elif instrument == 'MidcapNifty':
            symbol1 = "NSE:MIDCPNIFTY-INDEX"
            sym="NSE:MIDCPNIFTY"
        elif instrument == 'Sensex':
            symbol1 = "BSE:SENSEX-INDEX"
            sym="BSE:SENSEX"

     
        p = "2024-07-04"
        data1 = fetch_and_process_data(fyers, symbol1, p , p)
        delta1 = calculate_price_difference(data1)

        if contract == 'weekly':
            symbol3 =   sym + str(year) + str(month) + str(day) + str(strike_price) + option_type 
            symbol3 = str(symbol3)
        else:
            symbol3 = sym + str(year) + str(month) + str(strike_price) + option_type
            symbol3 = str(symbol3)
        
        data2 = fetch_and_process_data(fyers, symbol3, p , p)
        delta2 = calculate_price_difference(data2)
        
        delta = round(delta2 / delta1, 2)
        
        if contract == 'weekly':
            return render_template('delta.html', delta=delta , instrument=instrument , strike_price=strike_price , option_type=option_type)
        else:
            return render_template('delta.html', delta=delta, instrument=instrument , strike_price=strike_price , option_type=option_type)
    return render_template('delta.html')  # Render the initial form


def get_data():
    # Load the data from the Excel file
    df = pd.read_excel('data.xlsm', engine='openpyxl')

    # Extract NIFTY 50 data
    nifty_data = df[df['Column1.symbol'] == 'NIFTY 50'].iloc[0]

    # Filter out NIFTY 50 from the main DataFrame
    df = df[df['Column1.symbol'] != 'NIFTY 50']

    # Sort the data to find the top gainers and losers
    top_gainers = df.nlargest(3, 'Column1.pChange')
    top_losers = df.nsmallest(3, 'Column1.pChange')

    gainers = top_gainers[['Column1.symbol', 'Column1.lastPrice', 'Column1.pChange']].to_dict(orient='records')
    losers = top_losers[['Column1.symbol', 'Column1.lastPrice', 'Column1.pChange']].to_dict(orient='records')

    return gainers, losers, nifty_data

@app.route('/api/data')
def data():
    gainers, losers, nifty_data = get_data()
    nifty_info = {
        'symbol': nifty_data['Column1.symbol'],
        'lastPrice': nifty_data['Column1.lastPrice'],
        'pChange': nifty_data['Column1.pChange']
    }
    return jsonify({'gainers': gainers, 'losers': losers, 'nifty': nifty_info})


@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/generate_token_page')
def generate_token_page():
    return render_template('access.html')

@app.route('/generate-token', methods=['POST'])
def generate_token():
    appSession = fyersModel.SessionModel(
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        state=state,
        secret_key=secret_key,
        grant_type=grant_type
    )
    generateTokenUrl = appSession.generate_authcode()

    # Open the URL specifically in Google Chrome
    chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
    try:
        webbrowser.get(chrome_path).open(generateTokenUrl)
    except webbrowser.Error as e:
        return render_template('error.html', error=str(e))

    return render_template('auth_code.html', auth_code_url=generateTokenUrl)

@app.route('/callback')
def callback():
    auth_code = request.args.get('auth_code')
    if not auth_code:
        return render_template('callback.html', error="No auth code returned.")
    
    appSession = fyersModel.SessionModel(
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        state=state,
        secret_key=secret_key,
        grant_type=grant_type
    )
    appSession.set_token(auth_code)
    response = appSession.generate_token()
    try:
        access_token = response["access_token"]
        with open("access.txt", 'w') as file:
            file.write(access_token)
        
        # Get current date and time
        current_time = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
        
        return render_template('callback.html', access_generated=True, access_time=current_time)
    
    except Exception as e:
        return render_template('callback.html', error=str(e), response=response)


if __name__ == "__main__":
    app.run(debug=True)







