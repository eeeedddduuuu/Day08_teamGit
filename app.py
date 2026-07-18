"""
Team Content Review — Flask Application Entry
方向 A：智能数字媒体内容审核系统
"""
import os
import sys
from flask import Flask, jsonify

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from routes import register_blueprints


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB
    app.config['PROJECT_ROOT'] = PROJECT_ROOT
    app.config['OUTPUTS_DIR'] = os.path.join(PROJECT_ROOT, 'outputs')
    app.config['MODEL_PATH'] = os.path.join(PROJECT_ROOT, 'models', 'yolo11n.pt')

    # Ensure output directory exists
    os.makedirs(app.config['OUTPUTS_DIR'], exist_ok=True)

    # Register route blueprints
    register_blueprints(app)

    return app


app = create_app()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Team Content Review Server')
    parser.add_argument('--host', default='127.0.0.1', help='Bind host')
    parser.add_argument('--port', type=int, default=7880, help='Bind port')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)
