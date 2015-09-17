from flask import Flask, url_for, request, jsonify
import methods
import json
import os
app = Flask(__name__)

port = int(os.getenv('VCAP_APP_PORT', 8080))

with open('config.json') as data_file:    
    data = json.load(data_file)

host=data["host"]
user=data["username"]
pwd=data["password"]

@app.route('/')
def index():
    return 'Index Page'

@app.route('/hello')
def hello():
    return methods.hello()

@app.route('/debug/')
def debug():
    return jsonify(methods.debuger(host,user,pwd))

@app.route('/vms/', methods=['GET', 'POST'])
def get_vms():
    if request.method == 'POST':
        return 'your vms'
    else:
        return jsonify(vms = methods.get_all_vm_info(host,user,pwd))

@app.route('/vms/<uuid>/')
def get_vm(uuid):
    return jsonify(methods.find_vm_by_uuid(uuid,host,user,pwd))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
