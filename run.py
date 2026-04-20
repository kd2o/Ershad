from gevent import monkey
if not monkey.is_module_patched('os'): 
    monkey.patch_all()

import os
from backend import create_app, socketio

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)