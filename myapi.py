from flask import Flask, url_for, request, jsonify
import methods
import tools.cli as cli
app = Flask(__name__)

args = cli.get_args()
host=args.host
user=args.user
pwd=args.password
port=int(args.port)

@app.route('/')
def index():
    return 'Index Page'

@app.route('/hello')
def hello():
    return methods.hello()

@app.route('/checking')
def checking():
    return 'checking'

@app.route('/vms', methods=['GET', 'POST'])
def get_vms():
    if request.method == 'POST':
        return 'your vms'
    else:
        return methods.get_all_vm_info(host,user,pwd)

@app.route('/vms/<uuid>')
def get_vm(uuid):
    return methods.find_vm_by_uuid(uuid,host,user,pwd)

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
