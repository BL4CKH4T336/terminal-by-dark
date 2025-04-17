import os
import subprocess
from flask import Flask, request
from flask_socketio import SocketIO
import eventlet
eventlet.monkey_patch()

html_content = """
<!DOCTYPE html>
<html>
<head>
  <title>Web Terminal</title>
  <style>
    body { background: black; color: white; font-family: monospace; }
    #terminal { width: 100%%; height: 90vh; overflow-y: scroll; white-space: pre-wrap; padding: 10px; }
    input { width: 100%%; padding: 10px; font-size: 16px; background: #222; color: white; border: none; }
  </style>
</head>
<body>
  <div id="terminal"></div>
  <input id="commandInput" placeholder="Type command and press Enter" autofocus />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
  <script>
    const socket = io();
    const terminal = document.getElementById('terminal');
    const input = document.getElementById('commandInput');

    input.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        const cmd = input.value;
        terminal.innerHTML += '\\n> ' + cmd + '\\n';
        socket.emit('command', cmd);
        input.value = '';
      }
    });

    socket.on('output', function(data) {
      terminal.innerHTML += data + '\\n';
      terminal.scrollTop = terminal.scrollHeight;
    });
  </script>
</body>
</html>
"""

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return html_content

@socketio.on('command')
def handle_command(cmd):
    try:
        output = subprocess.getoutput(cmd)
        socketio.emit('output', output)
    except Exception as e:
        socketio.emit('output', str(e))

if __name__ == '__main__':
    print("Running Web Terminal at http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
