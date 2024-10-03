from flask import Flask, render_template
import mariadb, json

app = Flask(__name__)
app.config['DEBUG'] = True

#cmd admin privileges
#net start/stop MariaDB
config = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': 'super',
    'database': 'karate'
}

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('dashboard.html')

app.run()


