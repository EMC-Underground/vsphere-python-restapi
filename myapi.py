from flask import Flask, request, jsonify
import methods
import os
app = Flask(__name__)

# Uncomment if you need to debug the site
# app.debug = True

port = int(os.getenv('VCAP_APP_PORT', 8080))

# with open('config.json') as data_file:
#    data = json.load(data_file)
#
# host=data["host"]
# user=data["username"]
# pwd=data["password"]


@app.route('/')
def index():
    return 'Welcome to the VMware REST API!'


@app.route('/debug')
def debug():
    return methods.debugger()


@app.route('/vms/', methods=['GET', 'POST'])
def get_vms():
    if request.method == 'POST':
        specs = request.get_json()
        return jsonify(vm=methods.create_new_vm(specs))
    else:
        return jsonify(vm=methods.get_all_vm_info())


@app.route('/vms/<uuid>/', methods=['GET', 'PUT', 'DELETE'])
def get_vm(uuid):
    if request.method == 'DELETE':
        return methods.delete_vm_from_server(uuid)
    elif request.method == 'PUT':
        specs = request.get_json()
        return methods.change_vm_stats(uuid, specs)
    else:
        return jsonify(methods.find_vm_by_uuid(uuid))


@app.route('/vms/<uuid>/<attr>/', methods=['GET', 'PUT'])
def get_attr(uuid, attr):
    if request.method == 'GET':
        return methods.get_vm_attribute(uuid, attr)
    elif request.method == 'PUT' and attr.lower() == pxeboot
        specs = request.get_json()
        return methods.force_pxe_boot(uuid, specs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
