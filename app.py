import subprocess
from flask import Flask, Response
from flask_socketio import SocketIO
import eventlet
eventlet.monkey_patch()

html_content = """
<!DOCTYPE html>
<html>
<head>
  <title>Termux Web</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      margin: 0;
      padding: 0;
      background-color: black;
      color: #00ff00;
      font-family: monospace;
      font-size: 14px;
    }
    #terminal {
      padding: 10px;
      white-space: pre-wrap;
      word-wrap: break-word;
      height: 100vh;
      overflow-y: auto;
    }
    input {
      background: black;
      border: none;
      outline: none;
      color: #00ff00;
      font-family: monospace;
      font-size: 14px;
      width: 100%%;
    }
  </style>
</head>
<body>
  <div id="terminal" onclick="focusInput()"></div>
  <input id="input" autofocus autocomplete="off" />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
  <script>
    const terminal = document.getElementById('terminal');
    const input = document.getElementById('input');
    const socket = io();

    function focusInput() {
      input.focus();
    }

    function appendOutput(text) {
      terminal.innerHTML += text + "\\n";
      terminal.scrollTop = terminal.scrollHeight;
    }

    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        const cmd = input.value;
        appendOutput("> " + cmd);
        socket.emit('command', cmd);
        input.value = '';
      }
    });

    socket.on('output', function(data) {
      appendOutput(data);
    });

    window.onload = focusInput;
  </script>
</body>
</html>
"""

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return Response(html_content, mimetype='text/html')

@socketio.on('command')
def handle_command(cmd):
    try:
        output = subprocess.getoutput(cmd)
        socketio.emit('output', output)
    except Exception as e:
        socketio.emit('output', str(e))

if __name__ == '__main__':
    print("Web Terminal running at http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
