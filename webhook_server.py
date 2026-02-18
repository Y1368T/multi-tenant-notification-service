"""Simple webhook server to receive notification callbacks."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] CALLBACK RECEIVED!")
        print(f"{'='*60}")
        print(f"Path: {self.path}")
        print(f"\nBody:")
        try:
            data = json.loads(body.decode('utf-8'))
            print(json.dumps(data, indent=2))
        except:
            print(body.decode('utf-8'))
        print(f"{'='*60}\n")
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'received'}).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress default logging


if __name__ == '__main__':
    port = 9999
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    print(f'Webhook server listening on http://localhost:{port}')
    print('Waiting for callbacks...\n')
    server.serve_forever()
